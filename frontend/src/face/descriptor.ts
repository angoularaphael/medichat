const SIZE = 32;

export function faceDescriptorFromSource(
  source: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement,
): number[] {
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Canvas indisponible");
  }
  const width = "videoWidth" in source ? source.videoWidth || source.width : source.width;
  const height = "videoHeight" in source ? source.videoHeight || source.height : source.height;
  const side = Math.min(width || SIZE, height || SIZE);
  const sx = Math.max(0, ((width || SIZE) - side) / 2);
  const sy = Math.max(0, ((height || SIZE) - side) / 2);
  context.drawImage(source, sx, sy, side, side, 0, 0, SIZE, SIZE);
  const pixels = context.getImageData(0, 0, SIZE, SIZE).data;
  const values: number[] = [];
  for (let i = 0; i < pixels.length; i += 4) {
    values.push((0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2]) / 255);
  }
  const norm = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0)) || 1;
  return values.map((value) => value / norm);
}

export async function captureFaceSamples(
  video: HTMLVideoElement,
  count = 4,
  gapMs = 220,
): Promise<number[][]> {
  const samples: number[][] = [];
  for (let i = 0; i < count; i += 1) {
    samples.push(faceDescriptorFromSource(video));
    if (i < count - 1) {
      await new Promise((resolve) => window.setTimeout(resolve, gapMs));
    }
  }
  return samples;
}
