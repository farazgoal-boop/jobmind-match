"""Generate all app icons from root icon.png (owl logo)."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "icon.png"
STATIC = ROOT / "app" / "static"
MOBILE_RES = ROOT / "mobile-wrapper" / "resources"

WEB_SIZES = {
    "icon-16.png": 16,
    "icon-32.png": 32,
    "icon-48.png": 48,
    "icon-72.png": 72,
    "icon-96.png": 96,
    "icon-128.png": 128,
    "icon-192.png": 192,
    "icon-512.png": 512,
    "icon.png": 512,
    "apple-touch-icon.png": 180,
}

ANDROID_MIPMAP = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def remove_black_background(img: Image.Image, tolerance: int = 28) -> Image.Image:
    """Flood-fill black backdrop from corners; keeps owl pixels."""
    from collections import deque

    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def is_bg(r: int, g: int, b: int) -> bool:
        return r <= tolerance and g <= tolerance and b <= tolerance

    seen = set()
    q = deque()
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        q.append((x, y))

    while q:
        x, y = q.popleft()
        if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
            continue
        seen.add((x, y))
        r, g, b, a = px[x, y]
        if not is_bg(r, g, b):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    return img


def crop_to_content(img: Image.Image, padding: int = 24) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    cropped = img.crop(bbox)
    w, h = cropped.size
    side = max(w, h) + padding * 2
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = (side - w) // 2
    oy = (side - h) // 2
    canvas.paste(cropped, (ox, oy), cropped)
    return canvas


def resize_icon(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def save_web_icons(base: Image.Image) -> None:
    STATIC.mkdir(parents=True, exist_ok=True)
    for name, size in WEB_SIZES.items():
        out = STATIC / name
        resize_icon(base, size).save(out, "PNG", optimize=True)
        print(f"  web: {out.name} ({size}px)")


def save_mobile_resources(base: Image.Image) -> None:
    MOBILE_RES.mkdir(parents=True, exist_ok=True)
    for name, size in [("icon.png", 1024), ("splash.png", 2732)]:
        if name == "splash.png":
            splash = Image.new("RGBA", (1284, 2778), (7, 7, 15, 255))
            icon = resize_icon(base, 512)
            splash.paste(icon, ((1284 - 512) // 2, (2778 - 512) // 2 - 200), icon)
            splash.save(MOBILE_RES / name, "PNG", optimize=True)
        else:
            resize_icon(base, size).save(MOBILE_RES / name, "PNG", optimize=True)
        print(f"  mobile: resources/{name}")


def save_android_mipmaps(base: Image.Image) -> None:
    android_root = ROOT / "mobile-wrapper" / "android" / "app" / "src" / "main" / "res"
    if not android_root.exists():
        print("  android: skipped (run 'npx cap add android' first)")
        return
    for folder, size in ANDROID_MIPMAP.items():
        target = android_root / folder
        target.mkdir(parents=True, exist_ok=True)
        resize_icon(base, size).save(target / "ic_launcher.png", "PNG", optimize=True)
        resize_icon(base, size).save(target / "ic_launcher_round.png", "PNG", optimize=True)
        resize_icon(base, size).save(target / "ic_launcher_foreground.png", "PNG", optimize=True)
        print(f"  android: {folder} ({size}px)")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source icon: {SOURCE}")

    print(f"Source: {SOURCE}")
    img = Image.open(SOURCE)
    img = remove_black_background(img)
    img = crop_to_content(img, padding=20)

    # Keep root copy with transparent bg
    img.save(SOURCE, "PNG", optimize=True)
    print("  root: icon.png (transparent)")

    save_web_icons(img)
    save_mobile_resources(img)
    save_android_mipmaps(img)
    print("Done — owl icon applied everywhere.")


if __name__ == "__main__":
    main()
