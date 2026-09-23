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

  return (
    <div className={`plant-portrait ${compact ? "compact" : ""} ${kind}`}>
      {src ? <img src={src} alt={name} /> : <span className="plant-silhouette" aria-hidden="true" />}
    </div>
  );
}
