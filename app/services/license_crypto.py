"""Offline, machine-bound license verification using Ed25519 signatures.

Flow (mirrors Career Copilot Premium's request/response shape, swapping its
shared-secret HMAC for real asymmetric signing): the app derives a REQUEST
CODE from a stable per-machine fingerprint and shows it to the user, who
sends it to the seller. The seller runs scripts/generate_license.py (which
holds the ONLY copy of the private key, kept entirely outside this repo) to
sign that exact string, producing an ACTIVATION CODE. This module verifies
that signature using only the embedded PUBLIC key -- a public key reveals
nothing that lets anyone forge a new signature, unlike Career Copilot's
approach where the same secret both signs and verifies.

This module must never import or reference a private key. If a private key
ever needs to be loaded, that belongs in scripts/generate_license.py only.
"""
from __future__ import annotations

import base64
import hashlib
import os
import platform
import re
import subprocess
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback.
    winreg = None

REQUEST_PREFIX = "JMM"
ACTIVATION_PREFIX = "ACT"
_SIGNATURE_LEN = 64  # Ed25519 signatures are always exactly 64 bytes.

# Public key only -- generated once via `python scripts/generate_license.py
# --init-keys`, which prints this value for pasting in here. Safe to embed:
# an Ed25519 public key cannot be used to derive the private key or forge a
# signature, only to verify one already produced by the matching private key.
PUBLIC_KEY_B64 = "kJSV0sUJtS5aMLLMAs9zSs4d/1BEH0UizENVQeCFXac="


def machine_name() -> str:
    return (
        os.environ.get("COMPUTERNAME", "").strip()
        or platform.node().strip()
        or "Unknown PC"
    )


def _read_windows_machine_guid() -> str:
    if winreg is None:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip()
    except OSError:
        return ""


def _read_mac_platform_uuid() -> str:
    try:
        output = subprocess.check_output(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8", errors="ignore")
    except (OSError, subprocess.SubprocessError):
        return ""
    match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', output)
    return match.group(1).strip() if match else ""


def _read_linux_machine_id() -> str:
    for candidate in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return ""


def _read_stable_machine_id() -> str:
    system = platform.system()
    if system == "Windows":
        return _read_windows_machine_guid()
    if system == "Darwin":
        return _read_mac_platform_uuid()
    if system == "Linux":
        return _read_linux_machine_id()
    return ""


def machine_fingerprint() -> str:
    payload = "|".join(
        item for item in [_read_stable_machine_id(), machine_name()] if item
    )
    if not payload:
        payload = machine_name() or "jobmind-match"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()[:24]


def machine_request_code() -> str:
    """Not itself cryptographic material -- just a stable, human-shareable
    proxy for this machine's fingerprint. The seller signs this exact
    string; verification recomputes it locally and checks the signature
    against it, so a request code copied to a different machine won't
    produce a matching signature there."""
    fingerprint = machine_fingerprint()
    digest = hashlib.sha256(f"REQUEST::{fingerprint}".encode("utf-8")).hexdigest().upper()[:20]
    return _format_code(REQUEST_PREFIX, digest)


def _normalize_code(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def _format_code(prefix: str, raw: str) -> str:
    normalized = _normalize_code(raw)
    groups = [normalized[i : i + 5] for i in range(0, len(normalized), 5)]
    return "-".join([prefix] + groups)


def _b32_encode_signature(signature: bytes) -> str:
    return base64.b32encode(signature).decode("ascii").rstrip("=")


def _b32_decode_signature(encoded: str) -> bytes:
    # base32 requires the input length padded up to a multiple of 8.
    padded = encoded + "=" * (-len(encoded) % 8)
    return base64.b32decode(padded)


def format_activation_code(signature: bytes) -> str:
    if len(signature) != _SIGNATURE_LEN:
        raise ValueError(f"Expected a {_SIGNATURE_LEN}-byte Ed25519 signature")
    return _format_code(ACTIVATION_PREFIX, _b32_encode_signature(signature))


def verify_activation_code(request_code: str, activation_code: str) -> bool:
    """True only if activation_code is a valid Ed25519 signature (by the
    embedded public key) over the exact request_code string. Never raises
    -- malformed input, a tampered code, and a genuinely wrong signature
    are all just "not valid", since this sits directly in the untrusted
    activation request path."""
    try:
        normalized_activation = _normalize_code(activation_code)
        if not normalized_activation.startswith(ACTIVATION_PREFIX):
            return False
        raw = normalized_activation[len(ACTIVATION_PREFIX) :]
        signature = _b32_decode_signature(raw)
        if len(signature) != _SIGNATURE_LEN:
            return False
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64))
        public_key.verify(signature, _normalize_code(request_code).encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
    except Exception:
        # Any other decode/library failure on attacker-controlled input is
        # still just "not a valid code", not a 500.
        return False
