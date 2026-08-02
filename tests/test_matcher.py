"""Unit tests for app.services.matcher.rank_jobs — no DB, no app import."""
from app.services.matcher import rank_jobs


def _job(title: str, description: str, location: str = "Remote") -> dict:
    return {"title": title, "description": description, "location": location}


def test_empty_job_list_returns_empty():
    assert rank_jobs("python fastapi backend developer", [], top_k=5) == []


def test_stack_overlap_outranks_unrelated_job():
    candidate = "Experienced python fastapi backend developer, sqlalchemy, docker"
    jobs = [
        _job("Backend Python Engineer", "We use FastAPI, SQLAlchemy and Docker daily."),
        _job("Watercolor Painting Instructor", "Teach painting classes to beginners."),
    ]
    ranked = rank_jobs(candidate, jobs, top_k=5)

    assert len(ranked) == 2
    assert ranked[0]["job"]["title"] == "Backend Python Engineer"
    assert ranked[0]["score"] > ranked[1]["score"]
    assert "python" in ranked[0]["matched_skills"]


def test_senior_signal_downranks_relative_to_junior_equivalent():
    candidate = "python fastapi backend developer"
    jobs = [
        _job("Junior Backend Developer", "python fastapi backend role, entry level"),
        _job("Senior Staff Backend Manager", "python fastapi backend role, senior staff manager"),
    ]
    ranked = rank_jobs(candidate, jobs, top_k=5)

    by_title = {r["job"]["title"]: r["score"] for r in ranked}
    assert by_title["Junior Backend Developer"] > by_title["Senior Staff Backend Manager"]


def test_result_shape_has_expected_keys():
    candidate = "python developer"
    jobs = [_job("Python Developer", "python role")]
    ranked = rank_jobs(candidate, jobs, top_k=5)

    result = ranked[0]
    assert set(result.keys()) == {"job", "score", "reason", "matched_skills", "missing_skills"}
    assert isinstance(result["score"], float)
    assert isinstance(result["reason"], str)


def test_top_k_limits_results():
    candidate = "python developer"
    jobs = [_job(f"Job {i}", "python role") for i in range(10)]
    ranked = rank_jobs(candidate, jobs, top_k=3)
    assert len(ranked) == 3
