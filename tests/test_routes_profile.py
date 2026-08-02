from fastapi.testclient import TestClient

from app.main import app


def test_create_profile_returns_candidate():
    with TestClient(app) as client:
        resp = client.post(
            "/profile/",
            json={"full_name": "Ada Lovelace", "email": "ada@example.com", "skills_csv": "python,sql"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] is not None
        assert body["full_name"] == "Ada Lovelace"
        assert body["email"] == "ada@example.com"


def test_upload_cv_404_for_unknown_candidate():
    with TestClient(app) as client:
        resp = client.post(
            "/profile/999999/upload-cv",
            files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert resp.status_code == 404


def test_upload_cv_rejects_unsupported_extension():
    with TestClient(app) as client:
        created = client.post(
            "/profile/",
            json={"full_name": "Bob Builder", "email": "bob@example.com"},
        )
        candidate_id = created.json()["id"]

        resp = client.post(
            f"/profile/{candidate_id}/upload-cv",
            files={"file": ("resume.txt", b"plain text resume", "text/plain")},
        )
        assert resp.status_code == 400


def test_github_summary_404_for_unknown_candidate():
    with TestClient(app) as client:
        resp = client.get("/profile/999999/github")
        assert resp.status_code == 404
