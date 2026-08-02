from fastapi.testclient import TestClient
from sqlmodel import Session

import app.routes.jobs as jobs_route
from app.config import settings
from app.main import app
from app.models import CandidateProfile
from app.services.quota import consume_matches


def _fake_jobs(*args, **kwargs):
    return [
        {
            "source": "remotive",
            "title": "Python Backend Developer",
            "company": "Acme",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "description": "python fastapi backend role",
        }
    ]


def _create_candidate(client: TestClient) -> int:
    resp = client.post(
        "/profile/",
        json={"full_name": "Jobs Test", "email": f"jobs-{id(client)}@example.com", "skills_csv": "python,fastapi"},
    )
    return resp.json()["id"]


def test_get_matches_404_for_unknown_candidate(monkeypatch):
    monkeypatch.setattr(jobs_route, "fetch_jobs_from_sources", _fake_jobs)
    with TestClient(app) as client:
        resp = client.get("/jobs/match/999999")
        assert resp.status_code == 404


def test_get_matches_returns_ranked_jobs_and_usage(monkeypatch):
    monkeypatch.setattr(jobs_route, "fetch_jobs_from_sources", _fake_jobs)
    with TestClient(app) as client:
        candidate_id = _create_candidate(client)
        resp = client.get(f"/jobs/match/{candidate_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["matches"]) == 1
        assert body["matches_used"] == 1
        assert body["monthly_limit"] == settings.free_monthly_match_limit


def test_get_matches_402_once_quota_exceeded(monkeypatch, db_session: Session):
    monkeypatch.setattr(jobs_route, "fetch_jobs_from_sources", _fake_jobs)
    with TestClient(app) as client:
        candidate_id = _create_candidate(client)
        candidate = db_session.get(CandidateProfile, candidate_id)
        consume_matches(db_session, candidate, settings.free_monthly_match_limit)

        resp = client.get(f"/jobs/match/{candidate_id}")
        assert resp.status_code == 402
