"""Smoke tests for the dashboard render path and a few side-effect-free
JSON endpoints — no external network calls involved."""
from fastapi.testclient import TestClient

from app.main import app


def test_root_redirects_to_dashboard():
    with TestClient(app, follow_redirects=False) as client:
        resp = client.get("/")
        assert resp.status_code == 302
        assert resp.headers["location"] == "/dashboard"


def test_dashboard_renders_and_seeds_a_profile_when_db_is_empty():
    with TestClient(app) as client:
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


def test_license_status_shape():
    with TestClient(app) as client:
        resp = client.get("/api/license/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "activated" in body
        assert "masked_key" in body


def test_scrape_platforms_returns_registry_summary():
    with TestClient(app) as client:
        resp = client.get("/api/scrape/platforms")
        assert resp.status_code == 200
        body = resp.json()
        assert "platforms" in body
        assert "summary" in body
        assert len(body["platforms"]) > 0


def test_scrape_registry_returns_dedup_stats():
    with TestClient(app) as client:
        resp = client.get("/api/scrape/registry")
        assert resp.status_code == 200
        body = resp.json()
        assert "emails" in body
        assert "whatsapp" in body
