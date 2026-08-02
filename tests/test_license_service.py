"""Unit tests for app.services.license_service. Monkeypatches _env_path so no
test ever reads or writes the repo's real .env file."""
from sqlmodel import Session

import app.services.license_service as license_service
from app.services.license_service import activate_license, is_valid_format, license_status


def test_is_valid_format_accepts_gumroad_uuid_style_key():
    assert is_valid_format("A1B2C3D4-E5F6-1234-5678-9ABCDEF01234")


def test_is_valid_format_rejects_short_garbage():
    assert not is_valid_format("abc")


def test_is_valid_format_rejects_empty_string():
    assert not is_valid_format("")


def test_activate_license_rejects_invalid_format(db_session: Session, tmp_path, monkeypatch):
    monkeypatch.setattr(license_service, "_env_path", lambda: tmp_path / ".env")

    result = activate_license(db_session, "nope")
    assert result["ok"] is False


def test_activate_license_persists_app_settings_and_writes_env(db_session: Session, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr(license_service, "_env_path", lambda: env_file)

    key = "A1B2C3D4-E5F6-1234-5678-9ABCDEF01234"
    result = activate_license(db_session, key)

    assert result["ok"] is True
    assert env_file.exists()
    assert f"LICENSE_KEY={key}" in env_file.read_text(encoding="utf-8")

    status = license_status(db_session)
    assert status["activated"] is True
    assert status["masked_key"] == f"{key[:4]}…{key[-4:]}"
