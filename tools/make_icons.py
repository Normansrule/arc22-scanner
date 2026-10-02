#!/usr/bin/env python3
"""make_icons.py — draws the ARC-22 Studio app icon (PWA + desktop) with Pillow.
Writes docs/app/icons/icon-192.png, icon-512.png, icon-maskable-512.png and app/build/icon.png."""
import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
INK, HULL, CYAN = (23, 48, 61), (238, 242, 244), (26, 159, 219)


def draw(size: int, pad_frac: float) -> Image.Image:
    S = size * 4  # supersample
    im = Image.new("RGBA", (S, S), INK + (255,))
    d = ImageDraw.Draw(im)
    pad = S * pad_frac
    w = S - 2 * pad
    # D silhouette: straight rear (left), rounded bow (right)
    x0, y0, x1, y1 = pad + w * 0.14, pad + w * 0.16, pad + w * 0.86, pad + w * 0.84
    r = (y1 - y0) / 2
    d.rounded_rectangle((x0, y0, x1 - r * 0.6, y1), radius=w * 0.09, fill=HULL)
    d.ellipse((x1 - 2 * r * 0.75, y0, x1, y1), fill=HULL)
    # hand loop
    lx0, ly0 = x0 + w * 0.17, y0 + (y1 - y0) * 0.62
    d.rounded_rectangle((lx0, ly0, x1 - w * 0.2, y1 + 2), radius=w * 0.06, fill=INK)
    # cyan shoulder stripe + lens
    d.arc((x0 + w * 0.06, y0 + w * 0.06, x1 - w * 0.06, y1 - w * 0.06), start=-80, end=40, fill=CYAN,
          width=int(w * 0.045))
    cx, cy, lr = x1 - w * 0.13, y0 + (y1 - y0) * 0.28, w * 0.07
    d.ellipse((cx - lr, cy - lr, cx + lr, cy + lr), fill=CYAN)
    d.ellipse((cx - lr * 0.45, cy - lr * 0.45, cx + lr * 0.45, cy + lr * 0.45), fill=INK)
    return im.resize((size, size), Image.LANCZOS)


def main():
    out = ROOT / "docs" / "app" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    draw(192, 0.04).save(out / "icon-192.png")
    draw(512, 0.04).save(out / "icon-512.png")
    draw(512, 0.14).save(out / "icon-maskable-512.png")
    b = ROOT / "app" / "build"
    b.mkdir(parents=True, exist_ok=True)
    draw(512, 0.04).save(b / "icon.png")
    print("icons written")


if __name__ == "__main__":
    main()
