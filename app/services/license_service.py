"""Ed25519 machine-bound license activation (offline, no network call).

Signature verification and machine-fingerprint derivation live in
license_crypto.py; this module owns persistence (AppSetting DB rows +
.env, unchanged from the previous mechanism) and the activate/status
flow the API routes in app/routes/web.py call.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import Session

from app.models import AppSetting
from app.services.license_crypto import (
    machine_fingerprint,
    machine_request_code,
    verify_activation_code,
)

LICENSE_ACTIVATION_CODE = "license_activation_code"
LICENSE_FINGERPRINT = "license_fingerprint"
LICENSE_OK = "license_ok"

# Set only in the developer's own local .env, never in .env.example and
# never in a shipped/packaged build's .env -- lets local dev work without
# ever needing a real activation code. Mirrors Career Copilot Premium's
# equivalent dev bypass.
DEV_SKIP_ENV_VAR = "JOBMIND_DEV_SKIP_LICENSE"


def _env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _read_env_value(name: str) -> str:
    env_file = _env_path()
    if not env_file.exists():
        return ""
    prefix = f"{name}="
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _write_env_value(name: str, value: str) -> None:
    env_file = _env_path()
    prefix = f"{name}="
    lines: list[str] = []
    found = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(prefix):
                lines.append(f"{name}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{name}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def activate_license(session: Session, activation_code: str) -> dict:
    request_code = machine_request_code()
    if not verify_activation_code(request_code, activation_code):
        return {"ok": False, "message": "Invalid activation code for this computer."}

    cleaned = activation_code.strip().upper()
    fingerprint = machine_fingerprint()
    session.merge(AppSetting(key=LICENSE_ACTIVATION_CODE, value=cleaned))
    session.merge(AppSetting(key=LICENSE_FINGERPRINT, value=fingerprint))
    session.merge(AppSetting(key=LICENSE_OK, value="1"))
    session.commit()
    _write_env_value("LICENSE_ACTIVATION_CODE", cleaned)
    return {"ok": True, "message": "License activated. Welcome to JobMind Match Premium."}


def license_status(session: Session) -> dict:
    if os.environ.get("APP_ENV") == "android":
        return {"activated": True, "masked_key": "MOBI…LE", "platform": "android", "request_code": ""}

    if os.environ.get(DEV_SKIP_ENV_VAR, "").strip() == "1":
        return {"activated": True, "masked_key": "DEV MODE", "request_code": ""}

    request_code = machine_request_code()
    fingerprint = machine_fingerprint()

    code_row = session.get(AppSetting, LICENSE_ACTIVATION_CODE)
    fingerprint_row = session.get(AppSetting, LICENSE_FINGERPRINT)
    ok_row = session.get(AppSetting, LICENSE_OK)

    stored_code = code_row.value if code_row else ""
    stored_fingerprint = fingerprint_row.value if fingerprint_row else ""

    if not stored_code:
        # DB row missing but .env survived (e.g. DB was wiped/reinstalled
        # separately from .env) -- only trust it if it still verifies
        # against THIS machine's current request code, so this recovery
        # path can't be used to carry an activation onto a new machine.
        env_code = _read_env_value("LICENSE_ACTIVATION_CODE")
        if env_code and verify_activation_code(request_code, env_code):
            session.merge(AppSetting(key=LICENSE_ACTIVATION_CODE, value=env_code))
            session.merge(AppSetting(key=LICENSE_FINGERPRINT, value=fingerprint))
            session.merge(AppSetting(key=LICENSE_OK, value="1"))
            session.commit()
            stored_code = env_code
            stored_fingerprint = fingerprint

    activated = bool(
        stored_code
        and ok_row
        and ok_row.value == "1"
        and stored_fingerprint == fingerprint
        and verify_activation_code(request_code, stored_code)
    )

    return {
        "activated": activated,
        "masked_key": _mask(stored_code) if activated else "",
        "request_code": request_code,
    }


def _mask(code: str) -> str:
    if len(code) < 12:
        return ""
    return f"{code[:7]}…{code[-4:]}"
