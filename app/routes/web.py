from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models import ApplicationRecord, CandidateProfile
from app.services.assisted_apply import build_assisted_links
from app.services.cv_parser import extract_text_from_docx, extract_text_from_pdf
from app.services.matcher import rank_jobs
from app.services.quota import consume_matches, ensure_can_consume_matches
from app.services.source_registry import fetch_jobs_from_sources, free_sources_list

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def build_status_summary(applications: list[ApplicationRecord]) -> dict[str, int]:
    summary = {
        "total": len(applications),
        "saved": 0,
        "applied": 0,
        "replied": 0,
        "interview": 0,
        "rejected": 0,
    }
    for row in applications:
        key = row.status.strip().lower()
        if key in summary:
            summary[key] += 1
    return summary


def score_to_level(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def is_backend_job(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    backend_terms = ["python", "backend", "api", "fastapi", "django", "flask", "automation", "scrap"]
    frontend_terms = ["react", "frontend", "front end", "vue", "angular", "ui designer", "css"]
    has_backend = any(term in text for term in backend_terms)
    has_frontend = any(term in text for term in frontend_terms)
    return has_backend and not has_frontend


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: Annotated[Session, Depends(get_session)], candidate_id: int | None = None):
    profiles = session.exec(select(CandidateProfile).order_by(CandidateProfile.id.desc())).all()
    selected = session.get(CandidateProfile, candidate_id) if candidate_id else None
    applications = []
    if selected:
        applications = session.exec(
            select(ApplicationRecord)
            .where(ApplicationRecord.candidate_id == selected.id)
            .order_by(ApplicationRecord.updated_at.desc())
        ).all()
    status_summary = build_status_summary(applications)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profiles": profiles,
            "selected": selected,
            "matches": [],
            "usage": None,
            "error": "",
            "applications": applications,
            "status_summary": status_summary,
            "sources": ",".join(free_sources_list()),
        },
    )


@router.post("/dashboard/applications")
def add_application_from_form(
    candidate_id: Annotated[int, Form(...)],
    job_title: Annotated[str, Form(...)],
    company: Annotated[str, Form(...)],
    source: Annotated[str, Form(...)],
    job_url: Annotated[str, Form(...)],
    status: Annotated[str, Form()] = "saved",
    notes: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = ApplicationRecord(
        candidate_id=candidate_id,
        job_title=job_title,
        company=company,
        source=source,
        job_url=job_url,
        status=status,
        notes=notes,
    )
    session.add(row)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={candidate_id}", status_code=303)


@router.post("/dashboard/applications/{application_id}")
def update_application_from_form(
    application_id: int,
    candidate_id: Annotated[int, Form(...)],
    status: Annotated[str, Form(...)],
    notes: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = session.get(ApplicationRecord, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    row.status = status
    row.notes = notes
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={candidate_id}", status_code=303)


@router.post("/dashboard/profile")
def create_profile_from_form(
    full_name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    skills_csv: Annotated[str, Form(...)],
    github_username: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    profile = CandidateProfile(
        full_name=full_name,
        email=email,
        skills_csv=skills_csv,
        github_username=github_username,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return RedirectResponse(url=f"/dashboard?candidate_id={profile.id}", status_code=303)


@router.post("/dashboard/upload-cv")
async def upload_cv_from_form(
    candidate_id: Annotated[int, Form(...)],
    file: UploadFile = File(...),
    session: Annotated[Session, Depends(get_session)] = None,
):
    profile = session.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    content = await file.read()
    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        cv_text = extract_text_from_pdf(content)
    elif filename.endswith(".docx"):
        cv_text = extract_text_from_docx(content)
    else:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX supported")

    profile.cv_text = cv_text
    session.add(profile)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={profile.id}", status_code=303)


@router.get("/dashboard/matches", response_class=HTMLResponse)
def dashboard_matches(
    request: Request,
    candidate_id: int,
    top_k: int = 5,
    sources: str = "",
    min_match_level: str = "all",
    backend_only: bool = False,
    session: Annotated[Session, Depends(get_session)] = None,
):
    profiles = session.exec(select(CandidateProfile).order_by(CandidateProfile.id.desc())).all()
    selected = session.get(CandidateProfile, candidate_id)
    if not selected:
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "profiles": profiles,
                "selected": None,
                "matches": [],
                "usage": None,
                "error": "Candidate not found.",
                "applications": [],
                "status_summary": build_status_summary([]),
                "sources": ",".join(free_sources_list()),
            },
        )

    applications = session.exec(
        select(ApplicationRecord)
        .where(ApplicationRecord.candidate_id == selected.id)
        .order_by(ApplicationRecord.updated_at.desc())
    ).all()
    status_summary = build_status_summary(applications)

    selected_sources = [s.strip().lower() for s in sources.split(",") if s.strip()] or free_sources_list()
    if not selected.is_premium:
        selected_sources = selected_sources[:2]

    jobs = fetch_jobs_from_sources(selected_sources, limit_per_source=80)
    candidate_text = " ".join([selected.skills_csv, selected.cv_text])
    matches = rank_jobs(candidate_text=candidate_text, jobs=jobs, top_k=40)
    enriched_matches = []
    for item in matches:
        job = item["job"]
        level = score_to_level(float(item["score"]))
        if backend_only and not is_backend_job(job):
            continue
        if min_match_level in {"high", "medium", "low"}:
            if min_match_level == "high" and level != "high":
                continue
            if min_match_level == "medium" and level not in {"high", "medium"}:
                continue
        enriched_matches.append(
            {
                **item,
                "assisted_links": build_assisted_links(job["title"], job["company"]),
                "match_level": level,
            }
        )
    enriched_matches = enriched_matches[:top_k]

    error = ""
    usage = None
    try:
        ensure_can_consume_matches(session, selected, len(enriched_matches))
        usage = consume_matches(session, selected, len(enriched_matches))
    except ValueError as exc:
        error = str(exc)
        enriched_matches = []

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profiles": profiles,
            "selected": selected,
            "matches": enriched_matches,
            "usage": usage,
            "error": error,
            "sources": ",".join(selected_sources),
            "applications": applications,
            "status_summary": status_summary,
            "min_match_level": min_match_level,
            "backend_only": backend_only,
        },
    )
