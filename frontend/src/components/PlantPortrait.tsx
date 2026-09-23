import { PointerEvent, useEffect, useRef, useState } from "react";
import { plantPhoto } from "../plants/assets";

export default function PlantPortrait({
  code,
  name,
  compact = false,
}: {
  code: string;
  name: string;
  compact?: boolean;
}) {
  const src = plantPhoto(code);
  const kind = src ? "photo" : code;
  const [rotation, setRotation] = useState(0);
  const dragging = useRef(false);
  const lastX = useRef(0);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (compact || reduced) return;
    let frame = 0;
    let previous = performance.now();
    const tick = (now: number) => {
      const delta = now - previous;
      previous = now;
      if (!dragging.current) {
        setRotation((value) => value + delta * 0.035);
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [compact]);

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (compact) return;
    dragging.current = true;
    lastX.current = event.clientX;
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    const delta = event.clientX - lastX.current;
    lastX.current = event.clientX;
    setRotation((value) => value + delta * 0.55);
  }

  function onPointerUp() {
    dragging.current = false;
  }

  return (
    <div
      className={`plant-portrait ${compact ? "compact" : ""} ${kind}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      {src ? (
        <div className="plant-spinner" style={{ transform: `rotateY(${rotation}deg)` }}>
          <img className="plant-face front" src={src} alt={name} draggable={false} />
          <img className="plant-face back" src={src} alt="" draggable={false} />
        </div>
      ) : (
        <span className="plant-silhouette" aria-hidden="true" />
      )}
    </div>
  );
}
