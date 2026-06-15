"""Gumroad lifetime license activation (local, 1-PC honor system)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sqlmodel import Session, select

from app.models import AppSetting

LICENSE_KEY = "license_key"
LICENSE_OK = "license_ok"
LICENSE_PATTERN = re.compile(r"^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$", re.I)


def _env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _read_env_license() -> str:
    env_file = _env_path()
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("LICENSE_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _write_env_license(key: str) -> None:
    env_file = _env_path()
    lines: list[str] = []
    found = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("LICENSE_KEY="):
                lines.append(f"LICENSE_KEY={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"LICENSE_KEY={key}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_valid_format(key: str) -> bool:
    cleaned = (key or "").strip().upper()
    if LICENSE_PATTERN.match(cleaned):
        return True
    # Gumroad also uses shorter keys — accept 8+ alnum chunks with dashes
    return bool(re.match(r"^[A-Z0-9\-]{8,64}$", cleaned))


def activate_license(session: Session, key: str) -> dict:
    cleaned = (key or "").strip().upper()
    if not is_valid_format(cleaned):
        return {"ok": False, "message": "Invalid license key format."}

    fingerprint = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]
    session.merge(AppSetting(key=LICENSE_KEY, value=cleaned))
    session.merge(AppSetting(key=LICENSE_OK, value="1"))
    session.merge(AppSetting(key="license_fingerprint", value=fingerprint))
    session.commit()
    _write_env_license(cleaned)
    return {"ok": True, "message": "License activated. Welcome to JobMind Match Premium."}


def license_status(session: Session) -> dict:
    import os

    if os.environ.get("APP_ENV") == "android":
        return {"activated": True, "masked_key": "MOBI…LE", "platform": "android"}

    env_key = _read_env_license()
    row = session.get(AppSetting, LICENSE_KEY)
    ok_row = session.get(AppSetting, LICENSE_OK)
    active = bool((row and row.value) or env_key) and bool(ok_row and ok_row.value == "1" or env_key)
    if env_key and not row:
        session.merge(AppSetting(key=LICENSE_KEY, value=env_key.upper()))
        session.merge(AppSetting(key=LICENSE_OK, value="1"))
        session.commit()
        active = True
    return {
        "activated": active,
        "masked_key": _mask((row.value if row else env_key) or ""),
    }


def _mask(key: str) -> str:
    if len(key) < 8:
        return ""
    return f"{key[:4]}…{key[-4:]}"
