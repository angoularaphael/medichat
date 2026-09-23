import { lazy, Suspense } from "react";
import { plantPhoto } from "../plants/assets";

const PlantRelief = lazy(() => import("./PlantRelief"));

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

  if (src && !compact) {
    return (
      <Suspense fallback={<div className={`plant-portrait ${kind}`} />}>
        <PlantRelief src={src} name={name} />
      </Suspense>
    );
  }

  return (
    <div className={`plant-portrait compact ${kind}`}>
      {src ? <img src={src} alt={name} /> : <span className="plant-silhouette" aria-hidden="true" />}
    </div>
  );
}
