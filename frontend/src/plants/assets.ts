export const PLANT_PHOTOS: Record<string, string> = {
  thymus: "/plants/thymus.png",
  allium: "/plants/allium.png",
  artemisia: "/plants/artemisia.png",
  mentha: "/plants/mentha.png",
  spirulina: "/plants/spirulina.png",
  salix: "/plants/salix.png",
};

export function plantPhoto(code: string): string | undefined {
  return PLANT_PHOTOS[code];
}
