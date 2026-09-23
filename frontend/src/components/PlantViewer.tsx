import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Suspense, useMemo, useRef, useState } from "react";
import { Group } from "three";

const PALETTES: Record<string, { leaf: string; flower: string; stem: string }> = {
  thymus: { leaf: "#3d8f5a", flower: "#8b72ff", stem: "#2a5c3a" },
  allium: { leaf: "#4aa86a", flower: "#f2f0e8", stem: "#3d6b45" },
  artemisia: { leaf: "#8aa67a", flower: "#c9d4a8", stem: "#5c6e4a" },
  mentha: { leaf: "#2ecc71", flower: "#7bed9f", stem: "#1e7a45" },
  spirulina: { leaf: "#1abc9c", flower: "#48dbfb", stem: "#0e6b62" },
  salix: { leaf: "#c4d35a", flower: "#f0e68c", stem: "#6b7a32" },
  oryza: { leaf: "#7cb342", flower: "#f6e27a", stem: "#8d6e3a" },
  zingiber: { leaf: "#43a047", flower: "#ef6c00", stem: "#6d4c41" },
};

function PlantMesh({ code, spinning }: { code: string; spinning: boolean }) {
  const group = useRef<Group>(null);
  const palette = PALETTES[code] ?? PALETTES.thymus;

  useFrame((_, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * (spinning ? 1.8 : 0.35);
  });

  const leaves = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((index) => ({
        key: index,
        y: -0.15 + index * 0.18,
        rot: (index * Math.PI) / 2.5,
        scale: 0.85 - index * 0.08,
      })),
    []
  );

  if (code === "spirulina") {
    return (
      <group ref={group}>
        <mesh rotation={[0.6, 0.2, 0.4]}>
          <torusKnotGeometry args={[0.55, 0.14, 120, 16]} />
          <meshStandardMaterial color={palette.leaf} emissive={palette.flower} emissiveIntensity={0.2} />
        </mesh>
      </group>
    );
  }

  return (
    <group ref={group}>
      <mesh position={[0, -0.15, 0]}>
        <cylinderGeometry args={[0.045, 0.07, 1.35, 8]} />
        <meshStandardMaterial color={palette.stem} />
      </mesh>
      {leaves.map((leaf) => (
        <mesh key={leaf.key} position={[0, leaf.y, 0]} rotation={[0.7, leaf.rot, 0]} scale={leaf.scale}>
          <sphereGeometry args={[0.28, 16, 12]} />
          <meshStandardMaterial color={palette.leaf} roughness={0.55} />
        </mesh>
      ))}
      <mesh position={[0, 0.62, 0]}>
        <sphereGeometry args={[code === "allium" ? 0.28 : 0.18, 18, 18]} />
        <meshStandardMaterial color={palette.flower} emissive={palette.flower} emissiveIntensity={0.18} />
      </mesh>
    </group>
  );
}

export default function PlantViewer({ code }: { code: string }) {
  const [spinning, setSpinning] = useState(false);
  const reduced = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <div className="plant-3d">
      <Canvas camera={{ position: [0, 0.4, 3.1], fov: 42 }} dpr={[1, 1.5]} onPointerDown={() => setSpinning(true)}>
        <ambientLight intensity={0.45} />
        <pointLight position={[2, 3, 4]} intensity={12} color="#9be7ff" />
        <pointLight position={[-3, -1, 2]} intensity={8} color="#7d5cff" />
        <Suspense fallback={null}>
          <PlantMesh code={code} spinning={spinning && !reduced} />
        </Suspense>
        <OrbitControls enablePan={false} enableZoom={false} autoRotate={!reduced} autoRotateSpeed={spinning ? 8 : 1.4} />
      </Canvas>
      <span>Glisser ou cliquer pour faire tourner</span>
    </div>
  );
}
