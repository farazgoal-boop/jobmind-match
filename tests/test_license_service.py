"""Unit tests for the Ed25519 machine-bound license activation
(app.services.license_crypto + app.services.license_service).
Monkeypatches license_crypto.PUBLIC_KEY_B64 to a throwaway test keypair's
public key for every signature test -- must never depend on the real
developer private key (it lives outside the repo and doesn't exist in CI).
Monkeypatches _env_path so no test ever touches the repo's real .env."""
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlmodel import Session

import app.services.license_crypto as license_crypto
import app.services.license_service as license_service
from app.services.license_crypto import (
    _normalize_code,
    format_activation_code,
    machine_request_code,
    verify_activation_code,
)
from app.services.license_service import activate_license, license_status


def _public_b64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def _sign(private_key: Ed25519PrivateKey, request_code: str) -> str:
    # Must sign the NORMALIZED code (dashes stripped), same as
    # scripts/generate_license.py does -- verify_activation_code normalizes
    # before checking, so signing the raw dashed string here would produce
    # a signature over different bytes than what gets verified.
    signature = private_key.sign(_normalize_code(request_code).encode("utf-8"))
    return format_activation_code(signature)


def test_verify_activation_code_accepts_valid_signature(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_crypto, "PUBLIC_KEY_B64", _public_b64(private_key))

    request_code = "JMM-AAAAA-BBBBB-CCCCC-DDDDD"
    activation_code = _sign(private_key, request_code)
    assert verify_activation_code(request_code, activation_code)


def test_verify_activation_code_rejects_tampered_signature(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_crypto, "PUBLIC_KEY_B64", _public_b64(private_key))

    request_code = "JMM-AAAAA-BBBBB-CCCCC-DDDDD"
    activation_code = _sign(private_key, request_code)

    # Flip a bit in the actual decoded signature bytes, not a character in
    # the base32 text -- base32's last character in an incomplete 5-bit
    # group carries padding bits that don't map to any real signature byte,
    # so editing text at that position can (correctly) leave the decoded
    # bytes unchanged and make this test flaky. Byte-level tampering always
    # changes the signature that actually gets verified.
    raw = license_crypto._b32_decode_signature(_normalize_code(activation_code)[3:])
    tampered_bytes = bytes([raw[0] ^ 0x01]) + raw[1:]
    tampered = license_crypto.format_activation_code(tampered_bytes)
    assert not verify_activation_code(request_code, tampered)


def test_verify_activation_code_rejects_garbage():
    assert not verify_activation_code("JMM-AAAAA-BBBBB-CCCCC-DDDDD", "ACT-NOTAREALSIGNATURE")


def test_verify_activation_code_rejects_signature_from_a_different_machine(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_crypto, "PUBLIC_KEY_B64", _public_b64(private_key))

    activation_code = _sign(private_key, "JMM-AAAAA-BBBBB-CCCCC-DDDDD")
    assert not verify_activation_code("JMM-11111-22222-33333-44444", activation_code)


def test_verify_activation_code_rejects_wrong_signing_key(monkeypatch):
    real_key = Ed25519PrivateKey.generate()
    attacker_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_crypto, "PUBLIC_KEY_B64", _public_b64(real_key))

    request_code = "JMM-AAAAA-BBBBB-CCCCC-DDDDD"
    forged = _sign(attacker_key, request_code)
    assert not verify_activation_code(request_code, forged)


def test_activate_license_rejects_invalid_code(db_session: Session, tmp_path, monkeypatch):
    monkeypatch.setattr(license_service, "_env_path", lambda: tmp_path / ".env")
    result = activate_license(db_session, "ACT-NOTAREALSIGNATURE")
    assert result["ok"] is False


def test_activate_license_persists_and_survives_status_check(db_session: Session, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr(license_service, "_env_path", lambda: env_file)

    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(license_crypto, "PUBLIC_KEY_B64", _public_b64(private_key))

    request_code = machine_request_code()
    activation_code = _sign(private_key, request_code)

    result = activate_license(db_session, activation_code)
    assert result["ok"] is True
    assert env_file.exists()
    assert "LICENSE_ACTIVATION_CODE=" in env_file.read_text(encoding="utf-8")

    status = license_status(db_session)
    assert status["activated"] is True
    assert status["masked_key"]


def test_status_shows_request_code_when_not_activated(db_session: Session, tmp_path, monkeypatch):
    monkeypatch.setattr(license_service, "_env_path", lambda: tmp_path / ".env")
    status = license_status(db_session)
    assert status["activated"] is False
    assert status["request_code"].startswith("JMM-")


def test_dev_skip_env_var_bypasses_activation(monkeypatch, db_session: Session):
    monkeypatch.setenv(license_service.DEV_SKIP_ENV_VAR, "1")
    status = license_status(db_session)
    assert status["activated"] is True
