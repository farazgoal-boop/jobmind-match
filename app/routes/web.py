from datetime import datetime
import re
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

FOLLOW_UP_PATTERN = re.compile(r"\[follow-up:(\d{4}-\d{2}-\d{2})\]")


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


def build_company_summary(applications: list[ApplicationRecord]) -> list[dict[str, int | str]]:
    counts: dict[str, dict[str, int | str]] = {}
    for row in applications:
        bucket = counts.setdefault(
            row.company,
            {"company": row.company, "total": 0, "applied": 0, "interview": 0, "replied": 0},
        )
        bucket["total"] += 1
        status = row.status.strip().lower()
        if status in {"applied", "interview", "replied"}:
            bucket[status] += 1
    return sorted(counts.values(), key=lambda item: (-int(item["total"]), str(item["company"])))[:6]


def extract_follow_up_date(notes: str) -> str:
    match = FOLLOW_UP_PATTERN.search(notes or "")
    return match.group(1) if match else ""


def strip_follow_up_marker(notes: str) -> str:
    cleaned = FOLLOW_UP_PATTERN.sub("", notes or "")
    return cleaned.strip(" |")


def compose_notes(notes: str, follow_up_date: str) -> str:
    cleaned = strip_follow_up_marker(notes)
    marker = f"[follow-up:{follow_up_date}]" if follow_up_date else ""
    return " | ".join(part for part in [marker, cleaned] if part)


def build_tracker_entries(applications: list[ApplicationRecord]) -> list[dict]:
    entries = []
    for row in applications:
        entries.append(
            {
                "id": row.id,
                "candidate_id": row.candidate_id,
                "job_title": row.job_title,
                "company": row.company,
                "source": row.source,
                "job_url": row.job_url,
                "status": row.status,
                "notes": strip_follow_up_marker(row.notes),
                "follow_up_date": extract_follow_up_date(row.notes),
                "updated_at": row.updated_at,
            }
        )
    return entries


def build_follow_up_summary(applications: list[ApplicationRecord]) -> list[dict[str, str]]:
    items = []
    for row in applications:
        follow_up_date = extract_follow_up_date(row.notes)
        if not follow_up_date:
            continue
        items.append(
            {
                "company": row.company,
                "job_title": row.job_title,
                "follow_up_date": follow_up_date,
                "status": row.status,
            }
        )
    return sorted(items, key=lambda item: item["follow_up_date"])[:6]


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


def is_remote_job(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
    return any(term in text for term in ["remote", "work from home", "distributed", "anywhere"])


def is_junior_friendly_job(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    positive = ["junior", "entry", "associate", "graduate", "trainee", "intern"]
    negative = ["senior", "staff", "principal", "lead", "manager", "director"]
    return any(term in text for term in positive) or not any(term in text for term in negative)


def is_pakistan_friendly_job(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
    blocking_terms = ["us only", "usa only", "canada only", "europe only", "eu only", "uk only"]
    asia_terms = ["pakistan", "asia", "worldwide", "global", "anywhere", "remote"]
    return not any(term in text for term in blocking_terms) and any(term in text for term in asia_terms)


def has_salary_signal(job: dict) -> bool:
    salary = str(job.get("salary", "") or "").strip()
    text = f"{salary} {job.get('description', '')}".lower()
    return bool(salary) or any(term in text for term in ["salary", "compensation", "$", "usd", "eur", "per year"])


def has_visa_signal(job: dict) -> bool:
    if job.get("visa_support") is True:
        return True
    text = f"{job.get('description', '')} {job.get('location', '')}".lower()
    return any(term in text for term in ["visa", "sponsorship", "relocation"])


def matches_region(job: dict, region: str) -> bool:
    if region == "any":
        return True
    text = f"{job.get('location', '')} {job.get('description', '')}".lower()
    region_terms = {
        "pakistan": ["pakistan", "asia", "worldwide", "global", "remote"],
        "asia": ["asia", "singapore", "india", "pakistan", "uae", "remote"],
        "europe": ["europe", "eu", "germany", "france", "spain", "remote"],
        "americas": ["america", "americas", "usa", "canada", "latam", "remote"],
        "global": ["worldwide", "global", "anywhere", "remote"],
    }
    return any(term in text for term in region_terms.get(region, []))


def matches_search_focus(job: dict, search_focus: str) -> bool:
    if not search_focus or search_focus == "all":
        return True

    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    focus_terms = {
        "python": ["python", "django", "flask", "fastapi"],
        "fastapi": ["fastapi", "api", "backend"],
        "flask": ["flask", "python", "backend"],
        "fullstack": ["full stack", "full-stack", "backend", "frontend"],
    }
    return any(term in text for term in focus_terms.get(search_focus, []))


def build_match_summary(matches: list[dict]) -> dict[str, int]:
    summary = {"total": len(matches), "high": 0, "medium": 0, "low": 0, "remote": 0, "salary": 0, "visa": 0}
    for item in matches:
        level = item.get("match_level", "low")
        if level in summary:
            summary[level] += 1
        if is_remote_job(item.get("job", {})):
            summary["remote"] += 1
        if item.get("has_salary"):
            summary["salary"] += 1
        if item.get("has_visa_support"):
            summary["visa"] += 1
    return summary


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
            "applications": build_tracker_entries(applications),
            "status_summary": status_summary,
            "company_summary": build_company_summary(applications),
            "follow_up_summary": build_follow_up_summary(applications),
            "sources": ",".join(free_sources_list()),
            "min_match_level": "all",
            "backend_only": False,
            "remote_only": True,
            "junior_only": True,
            "search_focus": "python",
            "pakistan_friendly_only": True,
            "salary_only": False,
            "visa_support_only": False,
            "region_preference": "pakistan",
            "match_summary": build_match_summary([]),
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
    follow_up_date: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = ApplicationRecord(
        candidate_id=candidate_id,
        job_title=job_title,
        company=company,
        source=source,
        job_url=job_url,
        status=status,
        notes=compose_notes(notes, follow_up_date),
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
    follow_up_date: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = session.get(ApplicationRecord, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    row.status = status
    row.notes = compose_notes(notes, follow_up_date)
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
    remote_only: bool = True,
    junior_only: bool = True,
    search_focus: str = "python",
    pakistan_friendly_only: bool = True,
    salary_only: bool = False,
    visa_support_only: bool = False,
    region_preference: str = "pakistan",
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
                "company_summary": [],
                "follow_up_summary": [],
                "sources": ",".join(free_sources_list()),
                "min_match_level": min_match_level,
                "backend_only": backend_only,
                "remote_only": remote_only,
                "junior_only": junior_only,
                "search_focus": search_focus,
                "pakistan_friendly_only": pakistan_friendly_only,
                "salary_only": salary_only,
                "visa_support_only": visa_support_only,
                "region_preference": region_preference,
                "match_summary": build_match_summary([]),
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
        if remote_only and not is_remote_job(job):
            continue
        if junior_only and not is_junior_friendly_job(job):
            continue
        if pakistan_friendly_only and not is_pakistan_friendly_job(job):
            continue
        if salary_only and not has_salary_signal(job):
            continue
        if visa_support_only and not has_visa_signal(job):
            continue
        if not matches_region(job, region_preference):
            continue
        if not matches_search_focus(job, search_focus):
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
                "is_remote": is_remote_job(job),
                "is_junior_friendly": is_junior_friendly_job(job),
                "is_pakistan_friendly": is_pakistan_friendly_job(job),
                "has_salary": has_salary_signal(job),
                "has_visa_support": has_visa_signal(job),
                "search_query": f"{job['title']} {job['company']}",
            }
        )
    enriched_matches = enriched_matches[:top_k]
    match_summary = build_match_summary(enriched_matches)

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
            "applications": build_tracker_entries(applications),
            "status_summary": status_summary,
            "company_summary": build_company_summary(applications),
            "follow_up_summary": build_follow_up_summary(applications),
            "min_match_level": min_match_level,
            "backend_only": backend_only,
            "remote_only": remote_only,
            "junior_only": junior_only,
            "search_focus": search_focus,
            "pakistan_friendly_only": pakistan_friendly_only,
            "salary_only": salary_only,
            "visa_support_only": visa_support_only,
            "region_preference": region_preference,
            "match_summary": match_summary,
        },
    )
