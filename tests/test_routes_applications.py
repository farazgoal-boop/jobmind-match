from fastapi.testclient import TestClient

from app.main import app


def _create_candidate(client: TestClient) -> int:
    resp = client.post(
        "/profile/",
        json={"full_name": "Tracker Test", "email": f"tracker-{id(client)}@example.com"},
    )
    return resp.json()["id"]


def test_create_and_list_application_round_trips_follow_up_date():
    with TestClient(app) as client:
        candidate_id = _create_candidate(client)

        created = client.post(
            "/applications/",
            json={
                "candidate_id": candidate_id,
                "job_title": "Backend Engineer",
                "company": "Acme",
                "source": "remotive",
                "job_url": "https://example.com/job/1",
                "notes": "looks promising",
                "follow_up_date": "2026-09-01",
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["follow_up_date"] == "2026-09-01"
        assert body["notes"] == "looks promising"

        listed = client.get(f"/applications/{candidate_id}")
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 1
        assert rows[0]["follow_up_date"] == "2026-09-01"
        assert rows[0]["job_title"] == "Backend Engineer"


def test_update_application_changes_status():
    with TestClient(app) as client:
        candidate_id = _create_candidate(client)
        created = client.post(
            "/applications/",
            json={
                "candidate_id": candidate_id,
                "job_title": "Backend Engineer",
                "company": "Acme",
                "source": "remotive",
                "job_url": "https://example.com/job/2",
            },
        )
        app_id = created.json()["id"]

        updated = client.patch(
            f"/applications/{app_id}",
            json={"status": "interviewing", "notes": "phone screen done", "follow_up_date": ""},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "interviewing"
        assert updated.json()["notes"] == "phone screen done"


def test_update_application_404_for_unknown_id():
    with TestClient(app) as client:
        resp = client.patch(
            "/applications/999999",
            json={"status": "rejected", "notes": "", "follow_up_date": ""},
        )
        assert resp.status_code == 404
