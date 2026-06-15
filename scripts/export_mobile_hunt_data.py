"""Export hunt plan + platform summary for standalone mobile APK (no server)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.lead_platforms import PLATFORMS, get_hunt_plan, platform_summary

OUT = ROOT / "mobile-wrapper" / "www" / "data"
OUT.mkdir(parents=True, exist_ok=True)

chips = ["github", "reddit", "devto", "misc", "wahunt"]
payload = {
    "summary": platform_summary(),
    "platforms": [
        {"id": p["id"], "name": p["name"], "type": p["type"], "chip": p["chip"], "batches": p["batches"]}
        for p in PLATFORMS
    ],
    "hunt_plan": get_hunt_plan(chips),
}

(OUT / "hunt-data.json").write_text(json.dumps(payload, indent=0), encoding="utf-8")
print(f"Exported {payload['summary']['total']} platforms -> {OUT / 'hunt-data.json'}")
