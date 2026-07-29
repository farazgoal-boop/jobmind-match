"""Integration test: a short mocked hunt end-to-end, verifying leads land in
the database and are exportable — including the exact scenario Priority 0
is about: the export succeeding purely from disk, with nothing posted in
the request body, because the app "crashed" before ever calling
session/end and the in-page LEADS array never existed in this test."""
import csv
import io

from fastapi.testclient import TestClient
from sqlmodel import Session

import app.services.lead_hunter_engine as engine_mod
from app.main import app
from app.services.lead_hunter_registry import get_latest_session


def _fake_batch(tag: str) -> list[dict]:
    return [
        {
            "name": f"Jane Dev {tag}",
            "designation": "Full-stack Developer",
            "email": f"jane.{tag}@example.com",
            "whatsapp": "",
            "source": "github",
            "url": f"https://github.com/jane-{tag}",
            "notes": "",
            "location": "",
        },
        {
            "name": f"Sam Freelance {tag}",
            "designation": "Backend Developer",
            "email": f"sam.{tag}@example.com",
            "whatsapp": f"+1555{abs(hash(tag)) % 10000000:07d}",
            "source": "github",
            "url": f"https://github.com/sam-{tag}",
            "notes": "",
            "location": "",
        },
    ]


def _patch_single_batch(monkeypatch, batch: list[dict]) -> None:
    """Only the first fetch call returns leads — every later offset comes
    back empty, like a real source running dry."""
    call_count = {"n": 0}

    def fake_fetch_for_source(source, offset, keywords="", location=""):
        call_count["n"] += 1
        return batch if call_count["n"] == 1 else []

    monkeypatch.setattr(engine_mod, "fetch_for_source", fake_fetch_for_source)


def test_mocked_hunt_lands_in_db_and_is_exportable_after_simulated_crash(monkeypatch, fresh_engine):
    _patch_single_batch(monkeypatch, _fake_batch("export1"))

    with TestClient(app) as client:
        start = client.post("/api/scrape/session/start", data={"target": "sell", "keywords": "python"})
        assert start.status_code == 200
        session_id = start.json()["id"]

        batch = client.get(
            "/api/scrape/leads",
            params={"source": "github", "offset": 0, "session_id": session_id},
        )
        assert batch.status_code == 200
        body = batch.json()
        assert body["count"] == 2
        assert not body["error"]

        # No call to /api/scrape/session/{id}/end — this is the crash.
        # A brand-new connection to the same sqlite file (simulating the
        # process restarting) must already see both contacts, session
        # still marked "running".
        with Session(fresh_engine) as restarted_session:
            latest = get_latest_session(restarted_session)
            assert latest is not None
            assert latest["id"] == session_id
            assert latest["status"] == "running"
            assert latest["lead_count"] == 2

        # Export reads straight from the DB via session_id — no leads in
        # the POST body at all, proving export no longer depends on a
        # client-side array that a crash/reload would have wiped.
        export = client.post(
            "/api/scrape/export",
            params={"fmt": "csv", "filename": "test-export", "session_id": session_id},
            json={},
        )
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")

        rows = list(csv.reader(io.StringIO(export.text)))
        assert rows[0] == ["#", "Name", "Designation", "Email", "WhatsApp", "Source", "Profile URL", "Notes"]
        emails = {row[3] for row in rows[1:]}
        assert emails == {"jane.export1@example.com", "sam.export1@example.com"}


def test_export_rejects_when_no_body_and_no_session_id():
    with TestClient(app) as client:
        resp = client.post("/api/scrape/export", params={"fmt": "csv"}, json={})
        assert resp.status_code == 400


def test_session_leads_endpoint_returns_full_records_not_just_dedup_keys(monkeypatch):
    """Regression guard for the actual pre-fix bug: /api/scrape/registry only
    ever exposed email/whatsapp strings, never enough to rebuild a lead
    table or export file. The new endpoint must return full records."""
    _patch_single_batch(monkeypatch, _fake_batch("recordtest"))

    with TestClient(app) as client:
        start = client.post("/api/scrape/session/start", data={"target": "sell"})
        session_id = start.json()["id"]
        client.get(
            "/api/scrape/leads",
            params={"source": "github", "offset": 0, "session_id": session_id},
        )

        resp = client.get(f"/api/scrape/session/{session_id}/leads")
        assert resp.status_code == 200
        leads = resp.json()["leads"]
        assert len(leads) == 2
        names = {lead["name"] for lead in leads}
        assert names == {"Jane Dev recordtest", "Sam Freelance recordtest"}
        assert all(lead["url"].startswith("https://github.com/") for lead in leads)
        assert all(lead["email"].endswith("@example.com") for lead in leads)
