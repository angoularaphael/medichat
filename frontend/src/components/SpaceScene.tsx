import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Stars } from "@react-three/drei";
import { Suspense, useEffect, useRef, useState } from "react";
import { Group } from "three";

function Planet() {
  const group = useRef<Group>(null);
  useFrame((state, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * 0.08;
    group.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.18) * 0.08;
  });

  return (
    <group ref={group} rotation={[0.15, -0.45, 0.1]}>
      <Float speed={1.2} rotationIntensity={0.12} floatIntensity={0.25}>
        <mesh>
          <sphereGeometry args={[2.2, 96, 96]} />
          <MeshDistortMaterial
            color="#151052"
            emissive="#140b4b"
            emissiveIntensity={0.7}
            roughness={0.34}
            metalness={0.42}
            distort={0.18}
            speed={0.7}
          />
        </mesh>
        <mesh rotation={[1.2, 0.25, 0.3]}>
          <torusGeometry args={[3.15, 0.035, 12, 180]} />
          <meshBasicMaterial color="#73e6ff" transparent opacity={0.46} />
        </mesh>
        <mesh rotation={[1.05, 0.25, 0.3]}>
          <torusGeometry args={[3.55, 0.012, 8, 180]} />
          <meshBasicMaterial color="#9b7bff" transparent opacity={0.28} />
        </mesh>
      </Float>
    </group>
  );
}

export default function SpaceScene({ compact = false }: { compact?: boolean }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const narrow = window.matchMedia("(max-width: 520px)").matches;
    setEnabled(!reduced && !narrow);
  }, []);

  if (!enabled) return <div className="space-fallback" aria-hidden="true" />;

  return (
    <div className={`space-canvas ${compact ? "compact" : ""}`} aria-hidden="true">
      <Canvas
        camera={{ position: compact ? [0, 0, 8.5] : [0, 0, 7.5], fov: 48 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: "high-performance" }}
      >
        <ambientLight intensity={0.28} />
        <pointLight position={[4, 3, 6]} intensity={18} color="#65dcff" />
        <pointLight position={[-5, -2, 2]} intensity={13} color="#8354ff" />
        <Suspense fallback={null}>
          <Planet />
          <Stars radius={80} depth={35} count={1800} factor={3} fade speed={0.35} />
        </Suspense>
      </Canvas>
    </div>
  );
}
