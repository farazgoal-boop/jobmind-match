"""Create icon.ico from app/static/icon-256 or icon.png for Windows installer."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "static" / "icon.png"
OUT = ROOT / "app" / "static" / "icon.ico"

if not SRC.exists():
    raise SystemExit(f"Missing {SRC} — run generate_icons.py first")

img = Image.open(SRC).convert("RGBA")
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(OUT, format="ICO", sizes=[(s, s) for s in [16, 32, 48, 64, 128, 256]])
print(f"Created {OUT}")
