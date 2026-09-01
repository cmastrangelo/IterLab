"""Generate the IterLab mark and its favicons.

The mark is an inward spiral homing on a bright point — iteration converging
on the best result. Run from anywhere:

    python web/brand/generate_icons.py

Requires Pillow (`pip install pillow`). Writes:
    web/src/app/icon.png          256px  — browser tab icon (Next file metadata)
    web/src/app/apple-icon.png    180px  — iOS home-screen icon
    web/src/app/favicon.ico       16/32/48 — legacy
    web/public/iterlab-mark.png   96px   — sidebar / header lockup
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

WEB = Path(__file__).resolve().parent.parent
SS = 4  # supersample

# brand palette (globals.css --accent and friends)
INK_TOP = (36, 33, 64)
INK_BOT = (15, 17, 21)
ARM_OUT = (88, 80, 220)
ARM_IN = (208, 224, 255)
CORE = (234, 241, 255)
GLOW = (150, 172, 255, 150)


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def render(
    size: int, *, tile: bool = True, radius_frac: float = 0.235, compact: bool = False
) -> Image.Image:
    """The mark at `size` px. `tile` draws the rounded gradient background.
    `compact` = fewer turns / fatter arm, so it survives 16-32px favicons."""
    s = size * SS
    cx = cy = s / 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    if tile:
        grad = Image.new("RGB", (s, s), INK_TOP)
        gd = ImageDraw.Draw(grad)
        for y in range(s):
            gd.line([(0, y), (s, y)], fill=_lerp(INK_TOP, INK_BOT, y / s))
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, s - 1, s - 1], radius=int(s * radius_frac), fill=255
        )
        img.paste(grad, (0, 0), mask)

    # soft central glow
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gr = s * 0.13
    ImageDraw.Draw(glow).ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=GLOW)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.03)))

    d = ImageDraw.Draw(img)
    turns = 1.9 if compact else 2.7
    steps = 260
    r0, r1 = s * 0.36, s * 0.09
    wbase = 0.085 if compact else 0.052
    prev = None
    for i in range(steps + 1):
        t = i / steps
        ang = -math.pi / 2 + t * turns * 2 * math.pi
        rad = r0 + (r1 - r0) * (t**1.25)
        p = (cx + rad * math.cos(ang), cy + rad * math.sin(ang))
        if prev is not None:
            w = max(2, int(s * wbase * (0.4 + 0.6 * t)))
            col = _lerp(ARM_OUT, ARM_IN, t**0.7)
            d.line([prev, p], fill=col, width=w)
            d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=col)
        prev = p

    cr = s * (0.09 if compact else 0.055)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=CORE)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    (WEB / "src/app").mkdir(parents=True, exist_ok=True)
    (WEB / "public").mkdir(parents=True, exist_ok=True)

    render(256).save(WEB / "src/app/icon.png")
    render(180).save(WEB / "src/app/apple-icon.png")
    render(96).save(WEB / "public/iterlab-mark.png")
    # legacy .ico: at tiny sizes fill the frame + simplify so it still reads
    ico = render(64, radius_frac=0.5, compact=True)
    ico.save(WEB / "src/app/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    print("wrote:")
    for p in ("src/app/icon.png", "src/app/apple-icon.png",
              "src/app/favicon.ico", "public/iterlab-mark.png"):
        print(f"  web/{p}")


if __name__ == "__main__":
    main()
