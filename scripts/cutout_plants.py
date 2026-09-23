from pathlib import Path
from PIL import Image, ImageDraw
import cv2
import numpy as np

ROOT = Path(r"d:\PROBOOK 445 G7\Desktop\EIR")
OUT = ROOT / "frontend" / "public" / "plants"
PUBLIC = ROOT / "frontend" / "public"

SOURCES = {
    "thymus.png": "thymus.png",
    "allium-orbital.png": "allium.png",
    "artemisia-luna.png": "artemisia.png",
    "menthe.png": "mentha.png",
    "spiruline.png": "spirulina.png",
    "salix.png": "salix.png",
}


def _ellipse_mask(h: int, w: int, rx=0.42, ry=0.46, cy=0.5) -> np.ndarray:
    yy = (np.linspace(0, 1, h)[:, None] - cy) / ry
    xx = (np.linspace(0, 1, w)[None, :] - 0.5) / rx
    return (xx**2 + yy**2) <= 1.0


def grabcut(bgr: np.ndarray, mask: np.ndarray, iters: int = 5) -> np.ndarray:
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    keep = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    keep = cv2.medianBlur(keep, 5)
    keep = cv2.GaussianBlur(keep, (7, 7), 0)
    keep[keep < 40] = 0
    num, labels, stats, _ = cv2.connectedComponentsWithStats((keep > 40).astype(np.uint8), 8)
    min_area = keep.size * 0.012
    cleaned = np.zeros_like(keep)
    for index in range(1, num):
        if stats[index, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == index] = keep[labels == index]
    return cleaned


def mask_for(bgr: np.ndarray, name: str) -> np.ndarray:
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    band = max(6, min(h, w) // 18)
    mask[:band, :] = cv2.GC_BGD
    mask[-band:, :] = cv2.GC_BGD
    mask[:, :band] = cv2.GC_BGD
    mask[:, -band:] = cv2.GC_BGD
    center = _ellipse_mask(h, w)
    mask[center] = cv2.GC_PR_FGD

    if name == "mentha.png":
        green = (g > r + 8) & (g > b) & (g > 55)
        beige = (np.abs(r.astype(int) - g) < 40) & (np.abs(r.astype(int) - b) < 55) & (r > 120)
        mask[beige] = cv2.GC_BGD
        mask[green] = cv2.GC_FGD
    elif name == "artemisia.png":
        sky = (b > 130) & (b > r + 12) & (b >= g - 4)
        plant = ((r > 140) & (g > 140) & (b < 160)) | ((g > r) & (g > 50) & (b < 140))
        black = (r.astype(int) + g + b) < 90
        mask[sky | black] = cv2.GC_BGD
        mask[plant] = cv2.GC_FGD
    elif name == "thymus.png":
        fabric = (sat < 45) & (val < 140)
        plant = ((g > r + 6) & (g > 40)) | ((sat < 60) & (val > 150) & center)
        mask[fabric & ~center] = cv2.GC_BGD
        mask[plant & center] = cv2.GC_PR_FGD
        mask[_ellipse_mask(h, w, 0.36, 0.38)] = cv2.GC_FGD
    elif name == "allium.png":
        pink = ((hue > 125) | (hue < 20)) & (sat > 40) & (val > 70)
        green = (hue > 30) & (hue < 90) & (sat > 40)
        mask[green & ~center] = cv2.GC_BGD
        mask[pink] = cv2.GC_FGD
        mask[_ellipse_mask(h, w, 0.22, 0.22, 0.42)] = cv2.GC_PR_FGD
    elif name == "spirulina.png":
        white = (val > 200) & (sat < 50)
        seaweed = (hue > 30) & (hue < 95) & (g > 40)
        mask[white] = cv2.GC_BGD
        mask[: h // 8, :] = cv2.GC_BGD
        mask[seaweed & center] = cv2.GC_FGD
    elif name == "salix.png":
        sky = (b > r + 10) & (b > 130)
        mask[sky] = cv2.GC_BGD
        mask[~_ellipse_mask(h, w, 0.40, 0.44, 0.50)] = cv2.GC_BGD
        mask[_ellipse_mask(h, w, 0.30, 0.34, 0.50)] = cv2.GC_FGD

    return grabcut(bgr, mask)


def process_plants() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for source_name, dest_name in SOURCES.items():
        im = Image.open(ROOT / source_name).convert("RGB")
        im.thumbnail((900, 900), Image.Resampling.LANCZOS)
        rgb = np.array(im)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        alpha = mask_for(bgr, dest_name)
        rgb = rgb.copy()
        rgb[alpha < 20] = 0
        out = np.dstack([rgb, alpha])
        image = Image.fromarray(out, "RGBA")
        bbox = image.split()[-1].getbbox()
        if bbox:
            pad = 14
            l, t, r, b = bbox
            image = image.crop((max(0, l - pad), max(0, t - pad), min(image.width, r + pad), min(image.height, b + pad)))
        dest = OUT / dest_name
        image.save(dest, "PNG", optimize=True)
        opaque = (np.array(image)[:, :, 3] > 40).mean()
        print(f"wrote {dest_name} {image.size} opaque={opaque:.0%}")


def draw_favicon() -> None:
    def make(size: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), (7, 11, 24, 255))
        draw = ImageDraw.Draw(img)
        m = size / 32
        draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(8 * m), fill=(7, 11, 24, 255))
        cx = cy = size / 2
        draw.ellipse(
            (cx - 12 * m, cy - 5 * m, cx + 12 * m, cy + 5 * m),
            outline=(110, 231, 255, 255),
            width=max(1, int(1.4 * m)),
        )
        draw.ellipse(
            (cx - 6.2 * m, cy - 6.2 * m, cx + 6.2 * m, cy + 6.2 * m),
            outline=(100, 245, 189, 255),
            width=max(1, int(1.6 * m)),
        )
        draw.ellipse(
            (cx - 2.4 * m, cy - 2.4 * m, cx + 2.4 * m, cy + 2.4 * m),
            fill=(110, 231, 255, 255),
        )
        return img

    icon32 = make(32)
    icon32.save(PUBLIC / "favicon-32.png", "PNG")
    make(180).save(PUBLIC / "apple-touch-icon.png", "PNG")
    icon32.save(PUBLIC / "favicon.ico", sizes=[(32, 32)])
    print("wrote favicons")


if __name__ == "__main__":
    process_plants()
    draw_favicon()
