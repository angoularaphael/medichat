import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { ZoomIn, ZoomOut } from "lucide-react";
import { RefObject, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";

const COLS = 80;
const SIZE = 1.45;
const THICK = 0.22;

function buildSides(image: HTMLImageElement): THREE.BufferGeometry {
  const canvas = document.createElement("canvas");
  canvas.width = COLS;
  canvas.height = COLS;
  const context = canvas.getContext("2d");
  if (!context) return new THREE.BoxGeometry(0.2, 0.8, THICK * 2);

  context.clearRect(0, 0, COLS, COLS);
  const scale = Math.min(COLS / image.width, COLS / image.height) * 0.94;
  const drawW = image.width * scale;
  const drawH = image.height * scale;
  context.drawImage(image, (COLS - drawW) / 2, (COLS - drawH) / 2, drawW, drawH);
  const pixels = context.getImageData(0, 0, COLS, COLS).data;
  const solid = new Uint8Array(COLS * COLS);
  for (let i = 0; i < COLS * COLS; i += 1) {
    if (pixels[i * 4 + 3] > 18) solid[i] = 1;
  }

  const positions: number[] = [];
  const normals: number[] = [];
  const colors: number[] = [];
  const px = (x: number) => (x / COLS) * SIZE - SIZE / 2;
  const py = (y: number) => ((COLS - y) / COLS) * SIZE - SIZE / 2;
  const isSolid = (x: number, y: number) =>
    x >= 0 && y >= 0 && x < COLS && y < COLS && solid[y * COLS + x] === 1;

  const wall = (
    ax: number, ay: number,
    bx: number, by: number,
    nx: number, ny: number,
    r: number, g: number, b: number,
  ) => {
    const zf = THICK;
    const zb = -THICK;
    positions.push(ax, ay, zb, ax, ay, zf, bx, by, zb, ax, ay, zf, bx, by, zf, bx, by, zb);
    for (let i = 0; i < 6; i += 1) normals.push(nx, ny, 0);
    for (let i = 0; i < 6; i += 1) colors.push(r, g, b);
  };

  for (let y = 0; y < COLS; y += 1) {
    for (let x = 0; x < COLS; x += 1) {
      if (!solid[y * COLS + x]) continue;
      const index = (y * COLS + x) * 4;
      const r = (pixels[index] / 255) * 0.55;
      const g = (pixels[index + 1] / 255) * 0.55;
      const b = (pixels[index + 2] / 255) * 0.55;
      const x0 = px(x);
      const x1 = px(x + 1);
      const y0 = py(y);
      const y1 = py(y + 1);
      if (!isSolid(x - 1, y)) wall(x0, y0, x0, y1, -1, 0, r, g, b);
      if (!isSolid(x + 1, y)) wall(x1, y1, x1, y0, 1, 0, r, g, b);
      if (!isSolid(x, y - 1)) wall(x1, y0, x0, y0, 0, 1, r, g, b);
      if (!isSolid(x, y + 1)) wall(x0, y1, x1, y1, 0, -1, r, g, b);
    }
  }

  const geometry = new THREE.BufferGeometry();
  if (!positions.length) return new THREE.BoxGeometry(0.2, 0.8, THICK * 2);
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return geometry;
}

function ReliefMesh({ src }: { src: string }) {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [sides, setSides] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    let cancelled = false;
    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const face = document.createElement("canvas");
      face.width = 512;
      face.height = 512;
      const faceCtx = face.getContext("2d");
      if (faceCtx) {
        const scale = Math.min(512 / image.width, 512 / image.height) * 0.94;
        const drawW = image.width * scale;
        const drawH = image.height * scale;
        faceCtx.clearRect(0, 0, 512, 512);
        faceCtx.drawImage(image, (512 - drawW) / 2, (512 - drawH) / 2, drawW, drawH);
      }
      const map = new THREE.CanvasTexture(face);
      map.colorSpace = THREE.SRGBColorSpace;
      map.needsUpdate = true;
      setTexture(map);
      setSides(buildSides(image));
    };
    image.src = src;
    return () => {
      cancelled = true;
    };
  }, [src]);

  const faceMaterial = useMemo(() => {
    if (!texture) return null;
    return new THREE.MeshStandardMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.12,
      roughness: 0.45,
      metalness: 0.04,
      side: THREE.FrontSide,
    });
  }, [texture]);

  const sideMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.55,
        metalness: 0.06,
        side: THREE.DoubleSide,
      }),
    [],
  );

  if (!texture || !faceMaterial || !sides) return null;
  return (
    <group rotation={[0, 0.35, 0]}>
      <mesh position={[0, 0, THICK]} material={faceMaterial}>
        <planeGeometry args={[SIZE, SIZE]} />
      </mesh>
      <mesh position={[0, 0, -THICK]} rotation={[0, Math.PI, 0]} material={faceMaterial}>
        <planeGeometry args={[SIZE, SIZE]} />
      </mesh>
      <mesh geometry={sides} material={sideMaterial} />
    </group>
  );
}

type PlantReliefProps = {
  src: string;
  name: string;
  controlsRef: RefObject<OrbitControlsImpl | null>;
};

function Scene({ src, controlsRef }: { src: string; controlsRef: PlantReliefProps["controlsRef"] }) {
  return (
    <>
      <color attach="background" args={["#050816"]} />
      <ambientLight intensity={0.9} />
      <pointLight position={[2.2, 2.4, 3]} intensity={20} color="#9be7ff" />
      <pointLight position={[-2.4, -0.6, 1.6]} intensity={12} color="#7d5cff" />
      <directionalLight position={[0.2, 1, 2.2]} intensity={1.2} />
      <Suspense fallback={null}>
        <ReliefMesh src={src} />
      </Suspense>
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        enableRotate={false}
        enableZoom
        minDistance={1.15}
        maxDistance={3.2}
      />
    </>
  );
}

export default function PlantRelief({ src, name }: { src: string; name: string }) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);

  function zoom(delta: number) {
    const controls = controlsRef.current;
    if (!controls) return;
    const camera = controls.object;
    camera.position.z = Math.min(3.2, Math.max(1.15, camera.position.z + delta));
    controls.update();
  }

  return (
    <div className="plant-portrait photo">
      <Canvas
        camera={{ position: [0, 0.06, 2.15], fov: 36 }}
        dpr={[1, 1.35]}
        gl={{ antialias: true, alpha: true }}
        aria-label={name}
      >
        <Scene src={src} controlsRef={controlsRef} />
      </Canvas>
      <div className="plant-zoom-controls">
        <button type="button" className="plant-zoom-btn" onClick={() => zoom(-0.22)} aria-label="Zoomer">
          <ZoomIn size={18} />
        </button>
        <button type="button" className="plant-zoom-btn" onClick={() => zoom(0.22)} aria-label="Dezoomer">
          <ZoomOut size={18} />
        </button>
      </div>
    </div>
  );
}
