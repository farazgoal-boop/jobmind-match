from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import csv
import io
import json
import re
import random
import time
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import ApplicationRecord, CandidateProfile, ClientLead, FilterPreset
from app.services.assisted_apply import (
    build_assisted_links,
    build_client_access_links,
    build_live_search_links,
    build_sales_outreach_links,
)
from app.services.cv_parser import extract_text_from_docx, extract_text_from_pdf
from app.services.matcher import rank_jobs
from app.services.quota import consume_matches, ensure_can_consume_matches
from app.services.source_registry import fetch_jobs_from_sources, free_sources_list

router = APIRouter(tags=["web"])
from app.paths import templates_dir

templates = Jinja2Templates(directory=str(templates_dir()))
templates.env.globals["static_version"] = settings.asset_version

FOLLOW_UP_PATTERN = re.compile(r"\[follow-up:(\d{4}-\d{2}-\d{2})\]")
BUILTIN_RESUME_SOURCES = {
    "final-cv": {
        "label": "Muhammad Faraz Final CV",
        "path": Path(__file__).resolve().parents[2] / "docs" / "final-cv.md",
    }
}

DEFAULT_PROFILE_SEED = {
    "full_name": "Muhammad Faraz",
    "email": "farazgoal@gmail.com",
    "skills_csv": "Python,Flask,FastAPI,JavaScript,SQL,SQLite,HTML,CSS,TailwindCSS",
    "github_username": "farazgoal-boop",
    "resume_url": "",
    "portfolio_url": "https://muhammad-faraz-dev.netlify.app/",
    "linkedin_url": "https://www.linkedin.com/in/m-faraz-85b175179",
    "upwork_url": "https://www.upwork.com/freelancers/~018c67c9c97b482a3a?mp_source=share",
    "fiverr_url": "https://fiverr.com/s/qDKLLXX",
    "product_name": "JobMind Match",
    "product_url": "",
    "sales_pitch": "I build practical Python, FastAPI, Flask, and automation systems for business workflows and software teams.",
}

CLIENT_SEARCH_MODES = {"sell_services", "sell_products", "direct_clients"}


def resolve_ui_mode(search_mode: str) -> str:
    return "sell" if search_mode in CLIENT_SEARCH_MODES else "job"


def resolve_dashboard_ui_mode(request: Request, search_mode: str) -> str:
    """Honor ?active_mode=sell|job from mobile APK deep links."""
    query_mode = (request.query_params.get("active_mode") or "").strip().lower()
    if query_mode in {"sell", "job"}:
        return query_mode
    return resolve_ui_mode(search_mode)


def normalize_application_status(status: str) -> str:
    key = (status or "").strip().lower()
    if key == "replied":
        return "offer"
    return key or "saved"


def normalize_client_status(status: str) -> str:
    key = (status or "").strip().lower()
    if key == "new":
        return "discover"
    return key or "discover"


def build_resume_library() -> list[dict[str, str]]:
    library = []
    for key, item in BUILTIN_RESUME_SOURCES.items():
        path = item["path"]
        if path.exists():
            library.append({"key": key, "label": str(item["label"])})
    return library


def read_builtin_resume_text(source_key: str) -> str:
    source = BUILTIN_RESUME_SOURCES.get(source_key)
    if not source:
        raise HTTPException(status_code=404, detail="Resume source not found")

    path = source["path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume file is missing")

    return path.read_text(encoding="utf-8").strip()


def ensure_seed_profile(session: Session) -> CandidateProfile:
    existing = session.exec(select(CandidateProfile).order_by(CandidateProfile.id.desc())).first()
    if existing:
        updated = False
        if not existing.cv_text and build_resume_library():
            existing.cv_text = read_builtin_resume_text("final-cv")
            updated = True
        for field_name in ("portfolio_url", "linkedin_url", "upwork_url", "fiverr_url"):
            if not getattr(existing, field_name, ""):
                setattr(existing, field_name, DEFAULT_PROFILE_SEED[field_name])
                updated = True
        if updated:
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing

    profile = CandidateProfile(
        **DEFAULT_PROFILE_SEED,
        cv_text=read_builtin_resume_text("final-cv") if build_resume_library() else "",
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def build_status_summary(applications: list[ApplicationRecord]) -> dict[str, int]:
    summary = {
        "total": len(applications),
        "saved": 0,
        "applied": 0,
        "interview": 0,
        "offer": 0,
        "rejected": 0,
    }
    for row in applications:
        key = normalize_application_status(row.status)
        if key in summary:
            summary[key] += 1
    return summary


def build_company_summary(applications: list[ApplicationRecord]) -> list[dict[str, int | str]]:
    counts: dict[str, dict[str, int | str]] = {}
    for row in applications:
        bucket = counts.setdefault(
            row.company,
            {"company": row.company, "total": 0, "applied": 0, "interview": 0, "offer": 0},
        )
        bucket["total"] += 1
        status = normalize_application_status(row.status)
        if status in {"applied", "interview", "offer"}:
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
                "status": normalize_application_status(row.status),
                "notes": strip_follow_up_marker(row.notes),
                "follow_up_date": extract_follow_up_date(row.notes),
                "updated_at": row.updated_at.isoformat(),
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


def build_client_status_summary(leads: list[ClientLead]) -> dict[str, int]:
    summary = {
        "total": len(leads),
        "discover": 0,
        "contacted": 0,
        "replied": 0,
        "negotiation": 0,
        "won": 0,
        "lost": 0,
    }
    for row in leads:
        key = normalize_client_status(row.status)
        if key in summary:
            summary[key] += 1
    return summary


def build_client_lead_entries(leads: list[ClientLead]) -> list[dict]:
    return [
        {
            "id": row.id,
            "candidate_id": row.candidate_id,
            "lead_name": row.lead_name,
            "company": row.company,
            "source": row.source,
            "lead_url": row.lead_url,
            "contact_email": row.contact_email,
            "contact_phone": row.contact_phone,
            "contact_channel": row.contact_channel,
            "offer_type": row.offer_type,
            "status": normalize_client_status(row.status),
            "notes": row.notes,
            "follow_up_date": row.follow_up_date,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in leads
    ]


def build_filter_preset_entries(presets: list[FilterPreset]) -> list[dict[str, str | int]]:
    return [
        {
            "id": row.id,
            "candidate_id": row.candidate_id,
            "name": row.name,
            "preset_json": row.preset_json,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in presets
    ]


def build_client_follow_up_summary(leads: list[ClientLead]) -> list[dict[str, str]]:
    items = []
    for row in leads:
        if not row.follow_up_date:
            continue
        items.append(
            {
                "company": row.company,
                "lead_name": row.lead_name or "Decision maker",
                "follow_up_date": row.follow_up_date,
                "status": row.status,
            }
        )
    return sorted(items, key=lambda item: item["follow_up_date"])[:6]


def build_outreach_links(profile: CandidateProfile | None, offer_type: str) -> list[dict[str, str]]:
    if not profile:
        return []
    return build_sales_outreach_links(
        full_name=profile.full_name,
        email=profile.email,
        offer_type=offer_type,
        product_name=profile.product_name,
        product_url=profile.product_url,
        resume_url=profile.resume_url,
        portfolio_url=profile.portfolio_url,
        sales_pitch=profile.sales_pitch,
    )


def normalize_platform_targets(platform_targets: str) -> list[str]:
    selected_targets = [target.strip().lower() for target in platform_targets.split(",") if target.strip()]
    return selected_targets or ["indeed", "linkedin", "upwork", "google_clients"]


def resolve_selected_sources(request: Request, sources: str, is_premium: bool) -> list[str]:
    source_tokens = [source.strip().lower() for source in sources.split(",") if source.strip()]
    if "sources" in request.query_params and not source_tokens:
        return []

    selected_sources = source_tokens or free_sources_list()
    if not is_premium:
        selected_sources = selected_sources[:2]
    return selected_sources


def is_external_only_mode(search_mode: str, selected_sources: list[str], selected_platform_targets: list[str]) -> bool:
    external_job_targets = {"upwork", "fiverr", "linkedin"}
    return search_mode == "job_search" and not selected_sources and any(
        target in external_job_targets for target in selected_platform_targets
    )


def is_client_only_mode(search_mode: str, selected_sources: list[str], selected_platform_targets: list[str]) -> bool:
    client_modes = {"sell_services", "sell_products", "direct_clients"}
    return search_mode in client_modes and not selected_sources and bool(selected_platform_targets)


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
        "pakistan": ["pakistan"],
        "asia": ["asia", "singapore", "india", "pakistan", "uae", "japan", "malaysia"],
        "europe": ["europe", "eu", "germany", "france", "spain", "italy", "netherlands", "poland"],
        "americas": ["america", "americas", "usa", "united states", "canada", "latam", "brazil", "mexico"],
        "global": ["worldwide", "global", "anywhere", "remote"],
    }
    return any(term in text for term in region_terms.get(region, []))


def matches_search_focus(job: dict, search_focus: str) -> bool:
    if not search_focus or search_focus == "all":
        return True

    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    focus_terms = {
        "python": ["python", "django", "flask", "fastapi"],
        "fastapi": ["fastapi"],
        "flask": ["flask"],
        "fullstack": ["full stack", "full-stack", "backend", "frontend"],
    }
    return any(term in text for term in focus_terms.get(search_focus, []))


def parse_job_datetime(raw_value: str) -> datetime | None:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return None

    try:
        normalized = raw_text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw_text)
        except (TypeError, ValueError):
            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def matches_posted_window(job: dict, posted_within: str) -> bool:
    if posted_within in {"", "any"}:
        return True

    published_at = parse_job_datetime(job.get("published_at", ""))
    if published_at is None:
        return False

    day_windows = {
        "1d": 1,
        "3d": 3,
        "7d": 7,
        "14d": 14,
        "30d": 30,
    }
    max_age_days = day_windows.get(posted_within)
    if max_age_days is None:
        return True

    return published_at >= datetime.now(timezone.utc) - timedelta(days=max_age_days)


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


def compute_fit_score(score: float) -> int:
    return max(0, min(100, round(score * 100)))


def compute_trust_score(job: dict) -> int:
    score = 40
    source = str(job.get("source", "") or "").lower()
    description = str(job.get("description", "") or "").lower()
    location = str(job.get("location", "") or "").lower()
    url = str(job.get("url", "") or "").lower()

    trusted_sources = {
        "remotive": 18,
        "weworkremotely": 16,
        "arbeitnow": 14,
    }
    score += trusted_sources.get(source, 8)

    if has_salary_signal(job):
        score += 10
    if has_visa_signal(job):
        score += 6
    if is_remote_job(job):
        score += 6
    if any(token in description for token in ["apply", "benefits", "team", "requirements"]):
        score += 8
    if any(token in location for token in ["remote", "worldwide", "global"]):
        score += 4
    if url.startswith("https://"):
        score += 4

    return max(0, min(100, score))


def build_match_reasons(job: dict, matched_skills: list[str], missing_skills: list[str]) -> list[str]:
    reasons: list[str] = []
    if matched_skills:
        reasons.append(f"Stack match: {', '.join(matched_skills[:3])}")
    if is_remote_job(job):
        reasons.append("Remote-ready listing")
    if is_junior_friendly_job(job):
        reasons.append("Junior-friendly wording")
    if has_salary_signal(job):
        reasons.append("Compensation visible")
    if has_visa_signal(job):
        reasons.append("Visa or relocation signal")
    if is_pakistan_friendly_job(job):
        reasons.append("Pakistan-friendly access")
    if missing_skills:
        reasons.append(f"Upskill next: {', '.join(missing_skills[:2])}")
    return reasons[:5]


def build_active_filter_badges(
    search_mode: str,
    offer_type: str,
    client_type: str,
    contact_goal: str,
    posted_within: str,
    counterparty_type: str,
    trust_signal: str,
    company_size: str,
    proposal_pressure: str,
    verified_payment_only: bool,
) -> list[str]:
    badges = [
        f"Mode: {search_mode.replace('_', ' ')}",
        f"Offer: {offer_type.replace('_', ' ')}",
        f"Client: {client_type.replace('_', ' ')}",
        f"Goal: {contact_goal.replace('_', ' ')}",
    ]
    if posted_within != "any":
        badges.append(f"Posted: {posted_within}")
    if counterparty_type != "any":
        badges.append(f"Side: {counterparty_type.replace('_', ' ')}")
    if trust_signal != "any":
        badges.append(f"Trust: {trust_signal.replace('_', ' ')}")
    if company_size != "any":
        badges.append(f"Size: {company_size.replace('_', ' ')}")
    if proposal_pressure != "any":
        badges.append(f"Competition: {proposal_pressure}")
    if verified_payment_only:
        badges.append("Verified payment")
    return badges


def build_dashboard_live_links(
    profile: CandidateProfile | None,
    search_mode: str,
    offer_type: str,
    client_type: str,
    demand_level: str,
    contact_goal: str,
    counterparty_type: str,
    posted_within: str,
    verified_payment_only: bool,
    trust_signal: str,
    company_size: str,
    proposal_pressure: str,
    platform_targets: str,
    search_focus: str,
    region_preference: str,
    remote_only: bool,
    junior_only: bool,
    backend_only: bool,
    pakistan_friendly_only: bool,
    salary_only: bool,
    visa_support_only: bool,
    custom_keywords: str,
) -> list[dict[str, str]]:
    if not profile:
        return []

    return build_live_search_links(
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        demand_level=demand_level,
        contact_goal=contact_goal,
        counterparty_type=counterparty_type,
        posted_within=posted_within,
        verified_payment_only=verified_payment_only,
        trust_signal=trust_signal,
        company_size=company_size,
        proposal_pressure=proposal_pressure,
        platform_targets=[target.strip() for target in platform_targets.split(",") if target.strip()],
        search_focus=search_focus,
        region_preference=region_preference,
        remote_only=remote_only,
        junior_only=junior_only,
        backend_only=backend_only,
        pakistan_friendly_only=pakistan_friendly_only,
        salary_only=salary_only,
        visa_support_only=visa_support_only,
        candidate_skills=profile.skills_csv,
        custom_keywords=custom_keywords,
    )


def build_dashboard_client_links(
    profile: CandidateProfile | None,
    search_mode: str,
    offer_type: str,
    client_type: str,
    counterparty_type: str,
    region_preference: str,
    contact_goal: str,
    posted_within: str,
    verified_payment_only: bool,
    trust_signal: str,
    company_size: str,
    custom_keywords: str,
) -> list[dict[str, str]]:
    if not profile:
        return []

    return build_client_access_links(
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        counterparty_type=counterparty_type,
        region_preference=region_preference,
        contact_goal=contact_goal,
        posted_within=posted_within,
        verified_payment_only=verified_payment_only,
        trust_signal=trust_signal,
        company_size=company_size,
        custom_keywords=custom_keywords,
    )


def build_client_search_results(
    live_search_links: list[dict[str, str]],
    client_access_links: list[dict[str, str]],
    offer_type: str,
    client_type: str,
    contact_goal: str,
    counterparty_type: str,
    custom_keywords: str,
    top_k: int,
) -> list[dict[str, str]]:
    seen_urls: set[str] = set()
    query_focus = custom_keywords.strip() or client_type.replace("_", " ")
    target_label = counterparty_type.replace("_", " ") if counterparty_type != "any" else "decision maker"
    offer_label = offer_type.replace("_", " ")

    results: list[dict[str, str]] = []
    for link in [*live_search_links, *client_access_links]:
        url = str(link.get("url", "") or "").strip()
        platform = str(link.get("platform", "") or "Client Route").strip()
        caption = str(link.get("caption", "") or "Open buyer route").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        source_label = "Search Route" if link in live_search_links else "Client Access"
        company = f"{platform} {client_type.replace('_', ' ')} prospects".title()
        title = f"{platform} {offer_label.title()} buyers"
        notes = (
            f"Target {target_label} for {query_focus}. "
            f"Goal: {contact_goal.replace('_', ' ')}. "
            f"Route: {caption}."
        )
        results.append(
            {
                "title": title,
                "company": company,
                "platform": platform,
                "caption": caption,
                "url": url,
                "source": source_label,
                "query_focus": query_focus,
                "target_label": target_label,
                "notes": notes,
                "contact_channel": "linkedin" if "linkedin" in platform.lower() else "website",
                "lead_name": target_label.title(),
                "offer_type": offer_type,
                "follow_up_hint": "Open route, shortlist a real buyer, then save the lead below.",
            }
        )
        if len(results) >= top_k:
            break
    return results


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: Annotated[Session, Depends(get_session)], candidate_id: int | None = None):
    seed_profile = ensure_seed_profile(session)
    profiles = session.exec(select(CandidateProfile).order_by(CandidateProfile.id.desc())).all()
    selected = session.get(CandidateProfile, candidate_id) if candidate_id else seed_profile
    selected_platform_targets = normalize_platform_targets("indeed,linkedin")
    resume_library = build_resume_library()
    applications = []
    client_leads = []
    filter_presets = []
    if selected:
        applications = session.exec(
            select(ApplicationRecord)
            .where(ApplicationRecord.candidate_id == selected.id)
            .order_by(ApplicationRecord.updated_at.desc())
        ).all()
        client_leads = session.exec(
            select(ClientLead).where(ClientLead.candidate_id == selected.id).order_by(ClientLead.updated_at.desc())
        ).all()
        filter_presets = session.exec(
            select(FilterPreset).where(FilterPreset.candidate_id == selected.id).order_by(FilterPreset.name.asc())
        ).all()
    status_summary = build_status_summary(applications)
    client_status_summary = build_client_status_summary(client_leads)
    live_search_links = build_dashboard_live_links(
        profile=selected,
        search_mode="job_search",
        offer_type="software",
        client_type="startup",
        demand_level="latest",
        contact_goal="apply",
        counterparty_type="any",
        posted_within="7d",
        verified_payment_only=False,
        trust_signal="verified_company",
        company_size="any",
        proposal_pressure="any",
        platform_targets="indeed,linkedin",
        search_focus="python",
        region_preference="global",
        remote_only=True,
        junior_only=False,
        backend_only=True,
        pakistan_friendly_only=False,
        salary_only=False,
        visa_support_only=False,
        custom_keywords="",
    )
    client_access_links = build_dashboard_client_links(
        profile=selected,
        search_mode="direct_clients",
        offer_type="software",
        client_type="startup",
        counterparty_type="any",
        region_preference="global",
        contact_goal="pitch",
        posted_within="7d",
        verified_payment_only=False,
        trust_signal="any",
        company_size="any",
        custom_keywords="",
    )
    active_filter_badges = build_active_filter_badges(
        search_mode="job_search",
        offer_type="software",
        client_type="startup",
        contact_goal="apply",
        posted_within="7d",
        counterparty_type="any",
        trust_signal="any",
        company_size="any",
        proposal_pressure="any",
        verified_payment_only=False,
    )
    outreach_links = build_outreach_links(selected, "software")
    active_ui_mode = resolve_dashboard_ui_mode(request, "job_search")
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
            "client_leads": build_client_lead_entries(client_leads),
            "saved_filter_presets": build_filter_preset_entries(filter_presets),
            "status_summary": status_summary,
            "client_status_summary": client_status_summary,
            "company_summary": build_company_summary(applications),
            "follow_up_summary": build_follow_up_summary(applications),
            "client_follow_up_summary": build_client_follow_up_summary(client_leads),
            "live_search_links": live_search_links,
            "client_access_links": client_access_links,
            "outreach_links": outreach_links,
            "resume_library": resume_library,
            "sources": "remotive,weworkremotely,arbeitnow",
            "platform_targets": "indeed,linkedin",
            "selected_platform_targets": selected_platform_targets,
            "external_only_mode": False,
            "client_only_mode": False,
            "search_mode": "job_search",
            "offer_type": "software",
            "client_type": "startup",
            "demand_level": "latest",
            "contact_goal": "apply",
            "counterparty_type": "any",
            "posted_within": "7d",
            "verified_payment_only": False,
            "trust_signal": "verified_company",
            "company_size": "any",
            "proposal_pressure": "any",
            "custom_keywords": "",
            "min_match_level": "all",
            "backend_only": True,
            "remote_only": True,
            "junior_only": False,
            "search_focus": "python",
            "pakistan_friendly_only": False,
            "salary_only": False,
            "visa_support_only": False,
            "region_preference": "global",
            "active_ui_mode": active_ui_mode,
            "match_summary": build_match_summary([]),
            "active_filter_badges": active_filter_badges,
            "client_search_results": [],
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
        status=normalize_application_status(status),
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

    row.status = normalize_application_status(status)
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
    profile_id: Annotated[str | None, Form()] = None,
    github_username: Annotated[str, Form()] = "",
    resume_url: Annotated[str, Form()] = "",
    portfolio_url: Annotated[str, Form()] = "",
    linkedin_url: Annotated[str, Form()] = "",
    upwork_url: Annotated[str, Form()] = "",
    fiverr_url: Annotated[str, Form()] = "",
    product_name: Annotated[str, Form()] = "",
    product_url: Annotated[str, Form()] = "",
    sales_pitch: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    normalized_profile_id = int(profile_id) if profile_id and profile_id.strip() else None
    profile = session.get(CandidateProfile, normalized_profile_id) if normalized_profile_id else CandidateProfile()
    profile.full_name = full_name
    profile.email = email
    profile.skills_csv = skills_csv
    profile.github_username = github_username
    profile.resume_url = resume_url
    profile.portfolio_url = portfolio_url
    profile.linkedin_url = linkedin_url
    profile.upwork_url = upwork_url
    profile.fiverr_url = fiverr_url
    profile.product_name = product_name
    profile.product_url = product_url
    profile.sales_pitch = sales_pitch
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return RedirectResponse(url=f"/dashboard?candidate_id={profile.id}", status_code=303)


@router.post("/dashboard/client-leads")
def add_client_lead_from_form(
    candidate_id: Annotated[int, Form(...)],
    company: Annotated[str, Form(...)],
    lead_name: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "manual",
    lead_url: Annotated[str, Form()] = "",
    contact_email: Annotated[str, Form()] = "",
    contact_phone: Annotated[str, Form()] = "",
    contact_channel: Annotated[str, Form()] = "email",
    offer_type: Annotated[str, Form()] = "services",
    status: Annotated[str, Form()] = "discover",
    notes: Annotated[str, Form()] = "",
    follow_up_date: Annotated[str, Form()] = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = ClientLead(
        candidate_id=candidate_id,
        company=company,
        lead_name=lead_name,
        source=source,
        lead_url=lead_url,
        contact_email=contact_email,
        contact_phone=contact_phone,
        contact_channel=contact_channel,
        offer_type=offer_type,
        status=normalize_client_status(status),
        notes=notes,
        follow_up_date=follow_up_date,
    )
    session.add(row)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={candidate_id}", status_code=303)


@router.post("/dashboard/client-leads/{lead_id}")
def update_client_lead_from_form(
    lead_id: int,
    candidate_id: Annotated[int, Form(...)],
    status: Annotated[str, Form(...)],
    notes: Annotated[str, Form()] = "",
    follow_up_date: Annotated[str, Form()] = "",
    contact_email: Annotated[str, Form()] = "",
    contact_phone: Annotated[str, Form()] = "",
    contact_channel: Annotated[str, Form()] = "email",
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = session.get(ClientLead, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client lead not found")

    row.status = normalize_client_status(status)
    row.notes = notes
    row.follow_up_date = follow_up_date
    row.contact_email = contact_email
    row.contact_phone = contact_phone
    row.contact_channel = contact_channel
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={candidate_id}", status_code=303)


@router.post("/dashboard/filter-presets")
def save_filter_preset(
    candidate_id: Annotated[int, Form(...)],
    preset_name: Annotated[str, Form(...)],
    preset_payload: Annotated[str, Form(...)],
    session: Annotated[Session, Depends(get_session)] = None,
):
    candidate = session.get(CandidateProfile, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    name = preset_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Preset name required")

    try:
        payload = json.loads(preset_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid preset payload") from exc

    row = session.exec(
        select(FilterPreset).where(FilterPreset.candidate_id == candidate_id, FilterPreset.name == name)
    ).first()
    if row:
        row.preset_json = json.dumps(payload)
        row.updated_at = datetime.utcnow()
    else:
        row = FilterPreset(candidate_id=candidate_id, name=name, preset_json=json.dumps(payload))

    session.add(row)
    session.commit()
    session.refresh(row)
    return JSONResponse({"ok": True, "preset": build_filter_preset_entries([row])[0]})


@router.post("/dashboard/filter-presets/{preset_id}/delete")
def delete_filter_preset(
    preset_id: int,
    candidate_id: Annotated[int, Form(...)],
    session: Annotated[Session, Depends(get_session)] = None,
):
    row = session.get(FilterPreset, preset_id)
    if not row or row.candidate_id != candidate_id:
        raise HTTPException(status_code=404, detail="Preset not found")

    session.delete(row)
    session.commit()
    return JSONResponse({"ok": True, "preset_id": preset_id})


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


@router.post("/dashboard/import-cv")
def import_cv_from_library(
    candidate_id: Annotated[int, Form(...)],
    source_key: Annotated[str, Form(...)],
    session: Annotated[Session, Depends(get_session)] = None,
):
    profile = session.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    source_key = source_key.strip()
    if not source_key:
        raise HTTPException(status_code=400, detail="Choose a saved resume before importing")

    profile.cv_text = read_builtin_resume_text(source_key)
    session.add(profile)
    session.commit()
    return RedirectResponse(url=f"/dashboard?candidate_id={profile.id}", status_code=303)


@router.get("/dashboard/matches", response_class=HTMLResponse)
def dashboard_matches(
    request: Request,
    candidate_id: int,
    top_k: int = 5,
    sources: str = "",
    platform_targets: str = "indeed,linkedin",
    search_mode: str = "job_search",
    offer_type: str = "software",
    client_type: str = "startup",
    demand_level: str = "latest",
    contact_goal: str = "apply",
    counterparty_type: str = "any",
    posted_within: str = "7d",
    verified_payment_only: bool = False,
    trust_signal: str = "verified_company",
    company_size: str = "any",
    proposal_pressure: str = "any",
    custom_keywords: str = "",
    min_match_level: str = "all",
    backend_only: bool = True,
    remote_only: bool = True,
    junior_only: bool = False,
    search_focus: str = "python",
    pakistan_friendly_only: bool = False,
    salary_only: bool = False,
    visa_support_only: bool = False,
    region_preference: str = "global",
    session: Annotated[Session, Depends(get_session)] = None,
):
    profiles = session.exec(select(CandidateProfile).order_by(CandidateProfile.id.desc())).all()
    selected = session.get(CandidateProfile, candidate_id)
    selected_platform_targets = normalize_platform_targets(platform_targets)
    resume_library = build_resume_library()
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
                "client_leads": [],
                "status_summary": build_status_summary([]),
                "client_status_summary": build_client_status_summary([]),
                "company_summary": [],
                "follow_up_summary": [],
                "client_follow_up_summary": [],
                "live_search_links": [],
                "client_access_links": [],
                "outreach_links": [],
                "resume_library": resume_library,
                "sources": ",".join(free_sources_list()),
                "platform_targets": platform_targets,
                "selected_platform_targets": selected_platform_targets,
                "external_only_mode": False,
                "client_only_mode": False,
                "search_mode": search_mode,
                "offer_type": offer_type,
                "client_type": client_type,
                "demand_level": demand_level,
                "contact_goal": contact_goal,
                "counterparty_type": counterparty_type,
                "posted_within": posted_within,
                "verified_payment_only": verified_payment_only,
                "trust_signal": trust_signal,
                "company_size": company_size,
                "proposal_pressure": proposal_pressure,
                "custom_keywords": custom_keywords,
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
                "client_search_results": [],
            },
        )

    applications = session.exec(
        select(ApplicationRecord)
        .where(ApplicationRecord.candidate_id == selected.id)
        .order_by(ApplicationRecord.updated_at.desc())
    ).all()
    client_leads = session.exec(
        select(ClientLead).where(ClientLead.candidate_id == selected.id).order_by(ClientLead.updated_at.desc())
    ).all()
    filter_presets = session.exec(
        select(FilterPreset).where(FilterPreset.candidate_id == selected.id).order_by(FilterPreset.name.asc())
    ).all()
    status_summary = build_status_summary(applications)
    client_status_summary = build_client_status_summary(client_leads)

    selected_sources = resolve_selected_sources(request, sources, selected.is_premium)
    external_only_mode = is_external_only_mode(search_mode, selected_sources, selected_platform_targets)
    client_only_mode = is_client_only_mode(search_mode, selected_sources, selected_platform_targets)
    active_ui_mode = resolve_dashboard_ui_mode(request, search_mode)

    live_search_links = build_dashboard_live_links(
        profile=selected,
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        demand_level=demand_level,
        contact_goal=contact_goal,
        counterparty_type=counterparty_type,
        posted_within=posted_within,
        verified_payment_only=verified_payment_only,
        trust_signal=trust_signal,
        company_size=company_size,
        proposal_pressure=proposal_pressure,
        platform_targets=platform_targets,
        search_focus=search_focus,
        region_preference=region_preference,
        remote_only=remote_only,
        junior_only=junior_only,
        backend_only=backend_only,
        pakistan_friendly_only=pakistan_friendly_only,
        salary_only=salary_only,
        visa_support_only=visa_support_only,
        custom_keywords=custom_keywords,
    )
    client_access_links = build_dashboard_client_links(
        profile=selected,
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        counterparty_type=counterparty_type,
        region_preference=region_preference,
        contact_goal=contact_goal,
        posted_within=posted_within,
        verified_payment_only=verified_payment_only,
        trust_signal=trust_signal,
        company_size=company_size,
        custom_keywords=custom_keywords,
    )
    outreach_links = build_outreach_links(selected, offer_type)
    active_filter_badges = build_active_filter_badges(
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        contact_goal=contact_goal,
        posted_within=posted_within,
        counterparty_type=counterparty_type,
        trust_signal=trust_signal,
        company_size=company_size,
        proposal_pressure=proposal_pressure,
        verified_payment_only=verified_payment_only,
    )

    jobs = fetch_jobs_from_sources(selected_sources, limit_per_source=80) if not external_only_mode and not client_only_mode else []
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
        if not matches_posted_window(job, posted_within):
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
                "assisted_links": build_assisted_links(
                    job["title"],
                    job["company"],
                    candidate_name=selected.full_name,
                    candidate_email=selected.email,
                    resume_url=selected.resume_url,
                    portfolio_url=selected.portfolio_url,
                    github_username=selected.github_username,
                ),
                "match_level": level,
                "fit_score": compute_fit_score(float(item["score"])),
                "trust_score": compute_trust_score(job),
                "why_matched": build_match_reasons(job, item.get("matched_skills", []), item.get("missing_skills", [])),
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
    client_search_results = []
    if active_ui_mode == "sell":
        client_search_results = build_client_search_results(
            live_search_links=live_search_links,
            client_access_links=client_access_links,
            offer_type=offer_type,
            client_type=client_type,
            contact_goal=contact_goal,
            counterparty_type=counterparty_type,
            custom_keywords=custom_keywords,
            top_k=top_k,
        )

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
            "client_leads": build_client_lead_entries(client_leads),
            "saved_filter_presets": build_filter_preset_entries(filter_presets),
            "status_summary": status_summary,
            "client_status_summary": client_status_summary,
            "company_summary": build_company_summary(applications),
            "follow_up_summary": build_follow_up_summary(applications),
            "client_follow_up_summary": build_client_follow_up_summary(client_leads),
            "live_search_links": live_search_links,
            "client_access_links": client_access_links,
            "outreach_links": outreach_links,
            "resume_library": resume_library,
            "platform_targets": platform_targets,
            "selected_platform_targets": selected_platform_targets,
            "external_only_mode": external_only_mode,
            "client_only_mode": client_only_mode,
            "active_ui_mode": active_ui_mode,
            "search_mode": search_mode,
            "offer_type": offer_type,
            "client_type": client_type,
            "demand_level": demand_level,
            "contact_goal": contact_goal,
                "counterparty_type": counterparty_type,
                "posted_within": posted_within,
                "verified_payment_only": verified_payment_only,
                "trust_signal": trust_signal,
                "company_size": company_size,
                "proposal_pressure": proposal_pressure,
            "custom_keywords": custom_keywords,
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
            "active_filter_badges": active_filter_badges,
            "client_search_results": client_search_results,
        },
    )


# ──────────────────────────────────────────────────────────────────
#  NEW FEATURE 1: Duplicate Check
#  URL: GET /dashboard/client-leads/check-duplicate?email=...&phone=...
# ──────────────────────────────────────────────────────────────────
@router.get("/dashboard/client-leads/check-duplicate")
def check_lead_duplicate(
    session: Annotated[Session, Depends(get_session)],
    email: Optional[str] = None,
    phone: Optional[str] = None,
):
    if email:
        row = session.exec(
            select(ClientLead).where(ClientLead.contact_email == email)
        ).first()
        if row:
            return {"duplicate": True, "company": row.company, "lead_name": row.lead_name}

    if phone:
        clean_input = phone.replace(" ", "").replace("-", "").replace("+", "")
        all_leads = session.exec(select(ClientLead)).all()
        for row in all_leads:
            if row.contact_phone:
                stored = row.contact_phone.replace(" ", "").replace("-", "").replace("+", "")
                if stored == clean_input:
                    return {"duplicate": True, "company": row.company, "lead_name": row.lead_name}

    return {"duplicate": False}


# ──────────────────────────────────────────────────────────────────
#  NEW FEATURE 2: CSV Export
#  URL: GET /dashboard/client-leads/export-csv?candidate_id=1
# ──────────────────────────────────────────────────────────────────
@router.get("/dashboard/client-leads/export-csv")
def export_leads_csv(
    candidate_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    leads = session.exec(
        select(ClientLead)
        .where(ClientLead.candidate_id == candidate_id)
        .order_by(ClientLead.updated_at.desc())
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Company", "Contact Person", "Source",
        "Email", "WhatsApp/Phone", "Channel",
        "Offer Type", "Status", "Follow-up Date",
        "Notes", "Lead URL", "Updated At",
    ])
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.company,
            lead.lead_name or "",
            lead.source or "",
            lead.contact_email or "",
            lead.contact_phone or "",
            lead.contact_channel or "",
            lead.offer_type or "",
            lead.status,
            lead.follow_up_date or "",
            lead.notes or "",
            lead.lead_url or "",
            lead.updated_at.strftime("%Y-%m-%d %H:%M") if lead.updated_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )




# ══════════════════════════════════════════════════════════════════
#  LEAD HUNTER PRO — Maximum Power Scraper
#  Sources: GitHub (500+), Dev.to, HackerNews, IndieHackers,
#           RSS Feeds, Remotive, WeWorkRemotely, Freelancer boards
# ══════════════════════════════════════════════════════════════════

import requests as _req
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,7}')
_WA_RE    = re.compile(
    r'wa\.me/(\d{7,15})'
    r'|whatsapp\.com/send\?phone=(\d{7,15})'
    r'|whatsapp[:\s\-]+(\+?[\d][\d\s\-]{9,14})'
    r'|\bwa[:\s\-]+(\+?[\d][\d\s\-]{9,14})'
    r'|\+92[\s\-]?3\d{2}[\s\-]?\d{7}'
    r'|\+1[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}'
    r'|\+44[\s\-]?\d{10}'
    r'|\+91[\s\-]?\d{10}'
    r'|\+971[\s\-]?\d{9}',
    re.IGNORECASE
)

_SKIP_DOMAINS = {
    'example.com','test.com','email.com','domain.com','sentry.io',
    'github.com','google.com','cloudflare.com','w3.org','schema.org',
    'npmjs.com','pypi.org','jquery.com','wordpress.org','wix.com',
    'shopify.com','amazonaws.com','vercel.app','netlify.app',
    'heroku.com','railway.app','render.com','squarespace.com',
    'noreply.com','no-reply.com','notifications.com','support.com',
    'mailer.com','sendgrid.net','mailchimp.com','mailgun.org',
}

_HDRS = [
    {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'},
    {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'},
]

def _hdr(): return random.choice(_HDRS)

def _valid_email(e: str) -> bool:
    d = e.split('@')[-1].lower()
    return (
        d not in _SKIP_DOMAINS
        and '..' not in e
        and len(e) < 80
        and '.' in d
        and not e.startswith('.')
        and not e.endswith('.')
    )

def _extract(text: str) -> tuple[list, list]:
    """Extract emails and WhatsApp numbers from text"""
    emails = list({e for e in _EMAIL_RE.findall(text) if _valid_email(e)})

    wa = []
    # wa.me links
    for m in re.finditer(r'wa\.me/(\d{7,15})', text, re.I):
        wa.append('+' + m.group(1))
    # whatsapp.com/send?phone=
    for m in re.finditer(r'whatsapp\.com/send\?phone=(\d{7,15})', text, re.I):
        wa.append('+' + m.group(1))
    # "whatsapp: +923001234567" or "wa: +923001234567"
    for m in re.finditer(r'(?:whatsapp|wa)[:\s\-]+(\+?[\d][\d\s\-]{9,14})', text, re.I):
        n = re.sub(r'[\s\-]', '', m.group(1))
        if len(n) >= 10:
            wa.append(n if n.startswith('+') else '+' + n)
    # Phone numbers with country codes
    for pattern in [
        r'\+92[\s\-]?3\d{2}[\s\-]?\d{7}',  # Pakistan
        r'\+1[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}',  # USA
        r'\+44[\s\-]?\d{10}',  # UK
        r'\+91[\s\-]?\d{10}',  # India
        r'\+971[\s\-]?\d{9}',  # UAE
        r'\+966[\s\-]?\d{9}',  # Saudi
        r'\+61[\s\-]?\d{9}',   # Australia
        r'\+49[\s\-]?\d{10,11}', # Germany
    ]:
        for m in re.finditer(pattern, text):
            n = re.sub(r'[\s\-\(\)]', '', m.group(0))
            if len(n) >= 10:
                wa.append(n)

    return emails, list(set(wa))

def _desig(bio: str) -> str:
    if not bio: return ''
    for pat in [
        r'([\w\s]+developer)', r'([\w\s]+designer)',
        r'(freelance[\w\s]+)', r'([\w\s]+engineer)',
        r'([\w\s]+marketer)', r'([\w\s]+creator)',
        r'([\w\s]+consultant)', r'([\w\s]+writer)',
        r'([\w\s]+coach)', r'([\w\s]+seller)',
        r'([\w\s]+founder)', r'([\w\s]+maker)',
    ]:
        m = re.search(pat, bio, re.IGNORECASE)
        if m: return m.group(0).strip()[:50]
    return bio.split('.')[0][:50]


# ── SOURCE 1: GitHub Profiles (best for emails) ──────────────────

GH_SEARCH_QUERIES = [
    # Freelancers with emails
    'freelance developer email hire',
    'hire me developer email contact',
    'open to work email developer',
    'available for hire email developer',
    'freelance designer email hire',
    'freelance marketer email contact',
    'indie maker email contact',
    'solopreneur email hire',
    'python developer freelance email',
    'react developer freelance email',
    'fullstack developer freelance email',
    'web developer hire email contact',
    'mobile developer freelance email',
    'wordpress developer email hire',
    'shopify developer email contact',
    'django developer freelance email',
    'node developer freelance email',
    'flutter developer freelance email',
    'data scientist freelance email',
    'machine learning engineer email',
    'devops engineer freelance email',
    'blockchain developer email hire',
    'graphic designer email whatsapp hire',
    'UI UX designer email contact hire',
    'content creator email whatsapp',
    'digital marketer email whatsapp hire',
    'SEO expert email hire contact',
    'video editor email hire whatsapp',
    'copywriter email whatsapp hire',
    'virtual assistant email hire',
]

def _fetch_github_profiles(keyword: str, page: int = 1) -> list[dict]:
    """GitHub user profiles with public emails — page support for 500+ results"""
    leads = []
    try:
        url = f"https://api.github.com/search/users?q={_req.utils.quote(keyword)}&per_page=30&page={page}"
        r = _req.get(url, headers={'Accept': 'application/vnd.github.v3+json'}, timeout=15)
        if r.status_code == 422: return leads  # Bad query
        if r.status_code == 403: 
            time.sleep(10)
            return leads
        if r.status_code != 200: return leads

        users = r.json().get('items', [])
        for u in users[:20]:
            try:
                pr = _req.get(
                    f"https://api.github.com/users/{u['login']}",
                    headers={'Accept': 'application/vnd.github.v3+json'},
                    timeout=10
                )
                if pr.status_code != 200: continue
                p = pr.json()

                # Get all possible contact info
                email = p.get('email') or ''
                bio = f"{p.get('bio') or ''} {p.get('blog') or ''} {p.get('location') or ''} {p.get('company') or ''}"
                bio_emails, bio_wa = _extract(bio)

                if not email and bio_emails:
                    email = bio_emails[0]
                wa = bio_wa[0] if bio_wa else ''

                # Check blog URL for email
                blog = p.get('blog') or ''
                if blog and not email:
                    be, bw = _extract(blog)
                    email = be[0] if be else ''
                    if not wa and bw: wa = bw[0]

                if email or wa:
                    leads.append({
                        'name': p.get('name') or p.get('login', ''),
                        'designation': _desig(p.get('bio') or 'Developer'),
                        'email': email,
                        'whatsapp': wa,
                        'source': 'github',
                        'url': p.get('html_url', ''),
                        'notes': (p.get('bio') or '')[:100],
                    })
                time.sleep(0.2)
            except Exception:
                continue
    except Exception:
        pass
    return leads


def _fetch_github_readme(keyword: str, page: int = 1) -> list[dict]:
    """Search GitHub READMEs for contact info"""
    leads = []
    try:
        q = f"{keyword} email in:readme"
        url = f"https://api.github.com/search/repositories?q={_req.utils.quote(q)}&per_page=20&sort=updated&page={page}"
        r = _req.get(url, headers={'Accept': 'application/vnd.github.v3+json'}, timeout=15)
        if r.status_code != 200: return leads

        for repo in r.json().get('items', [])[:12]:
            try:
                owner = repo.get('owner', {}).get('login', '')
                rname = repo.get('name', '')
                # Try main then master branch
                for branch in ['main', 'master']:
                    rm = _req.get(
                        f"https://raw.githubusercontent.com/{owner}/{rname}/{branch}/README.md",
                        timeout=8
                    )
                    if rm.status_code == 200:
                        emails, wa = _extract(rm.text)
                        if emails or wa:
                            leads.append({
                                'name': owner,
                                'designation': _desig(repo.get('description') or 'Developer'),
                                'email': emails[0] if emails else '',
                                'whatsapp': wa[0] if wa else '',
                                'source': 'github',
                                'url': repo.get('html_url', ''),
                                'notes': (repo.get('description') or '')[:100],
                            })
                        break
                time.sleep(0.25)
            except Exception:
                continue
    except Exception:
        pass
    return leads


# ── SOURCE 2: Dev.to (great for developer emails) ────────────────

DEVTO_TAGS = [
    'forhire', 'freelance', 'hiring', 'opentowork', 'career',
    'developer', 'webdev', 'python', 'javascript', 'react',
    'node', 'fullstack', 'backend', 'frontend', 'devops',
    'design', 'ux', 'marketing', 'productivity', 'startup',
]

def _fetch_devto_articles(tag: str, page: int = 1) -> list[dict]:
    """Dev.to articles — fetch full body for contact info"""
    leads = []
    try:
        r = _req.get(
            f"https://dev.to/api/articles?tag={tag}&per_page=20&page={page}",
            headers=_hdr(), timeout=12
        )
        if r.status_code != 200: return leads
        for a in r.json():
            try:
                # Get full article with body
                art_id = a.get('id', '')
                if not art_id: continue
                ar = _req.get(
                    f"https://dev.to/api/articles/{art_id}",
                    headers=_hdr(), timeout=10
                )
                if ar.status_code != 200: continue
                full = ar.json()
                body = full.get('body_markdown', '') or full.get('body_html', '') or ''
                # Clean HTML tags
                body_clean = re.sub(r'<[^>]+>', ' ', body)
                txt = f"{a.get('title','')} {a.get('description','')} {body_clean}"
                emails, wa = _extract(txt)
                if emails or wa:
                    user = a.get('user', {})
                    leads.append({
                        'name': user.get('name', ''),
                        'designation': _desig(a.get('title', '')),
                        'email': emails[0] if emails else '',
                        'whatsapp': wa[0] if wa else '',
                        'source': 'devto',
                        'url': a.get('url', ''),
                        'notes': a.get('title', '')[:100],
                    })
                time.sleep(0.15)
            except Exception:
                continue
    except Exception:
        pass
    return leads


# ── SOURCE 3: HackerNews (great for dev emails) ──────────────────

def _fetch_hackernews() -> list[dict]:
    """HackerNews Who Is Hiring + Freelancer threads"""
    leads = []
    try:
        # Search for hiring/freelance posts via Algolia
        for query in ['Ask HN Who is hiring', 'Ask HN Freelancer']:
            r = _req.get(
                f'https://hn.algolia.com/api/v1/search?query={_req.utils.quote(query)}&tags=story&hitsPerPage=3',
                timeout=12
            )
            if r.status_code != 200: continue
            for hit in r.json().get('hits', [])[:2]:
                story_id = hit.get('objectID', '')
                if not story_id: continue
                # Get comments
                sr = _req.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                    timeout=10
                )
                if sr.status_code != 200: continue
                kids = (sr.json().get('kids') or [])[:100]
                for kid_id in kids:
                    try:
                        kr = _req.get(
                            f'https://hacker-news.firebaseio.com/v0/item/{kid_id}.json',
                            timeout=8
                        )
                        if kr.status_code != 200: continue
                        k = kr.json()
                        txt = re.sub(r'<[^>]+>', ' ', k.get('text', '') or '')
                        emails, wa = _extract(txt)
                        if emails or wa:
                            leads.append({
                                'name': k.get('by', ''),
                                'designation': _desig(txt[:200]),
                                'email': emails[0] if emails else '',
                                'whatsapp': wa[0] if wa else '',
                                'source': 'hackernews',
                                'url': f"https://news.ycombinator.com/item?id={k.get('id','')}",
                                'notes': txt[:100],
                            })
                        time.sleep(0.1)
                    except Exception:
                        continue
    except Exception:
        pass
    return leads


# ── SOURCE 4: IndieHackers ───────────────────────────────────────

def _fetch_indiehackers() -> list[dict]:
    leads = []
    try:
        r = _req.get('https://www.indiehackers.com/api/posts?limit=50', timeout=12)
        if r.status_code != 200: return leads
        for p in r.json()[:30]:
            txt = f"{p.get('title','')} {p.get('content','')}"
            emails, wa = _extract(txt)
            if emails or wa:
                leads.append({
                    'name': p.get('userDisplayName', ''),
                    'designation': _desig(p.get('title', '')),
                    'email': emails[0] if emails else '',
                    'whatsapp': wa[0] if wa else '',
                    'source': 'indiehackers',
                    'url': f"https://www.indiehackers.com{p.get('url','')}",
                    'notes': p.get('title', '')[:100],
                })
    except Exception:
        pass
    return leads


# ── SOURCE 5: RSS Feeds from Job Boards ─────────────────────────

def _fetch_remotive_rss() -> list[dict]:
    """Remotive.com RSS — remote jobs with company emails"""
    leads = []
    try:
        r = _req.get('https://remotive.com/remote-jobs/feed', headers=_hdr(), timeout=15)
        if r.status_code != 200: return leads
        root = ET.fromstring(r.content)
        ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
        for item in root.findall('.//item')[:30]:
            title = (item.findtext('title') or '')
            company = (item.findtext('author') or '')
            link = (item.findtext('link') or '')
            desc = (item.findtext('description') or '')
            content = (item.find('content:encoded', ns) or item.find('{http://purl.org/rss/1.0/modules/content/}encoded'))
            body = content.text if content is not None else ''
            txt = f"{title} {company} {desc} {body}"
            txt_clean = re.sub(r'<[^>]+>', ' ', txt)
            emails, wa = _extract(txt_clean)
            if emails or wa:
                leads.append({
                    'name': company or title[:40],
                    'designation': _desig(title),
                    'email': emails[0] if emails else '',
                    'whatsapp': wa[0] if wa else '',
                    'source': 'remotive',
                    'url': link,
                    'notes': title[:100],
                })
    except Exception:
        pass
    return leads


def _fetch_weworkremotely_rss() -> list[dict]:
    """WeWorkRemotely RSS feeds"""
    leads = []
    feeds = [
        'https://weworkremotely.com/remote-jobs.rss',
        'https://weworkremotely.com/categories/remote-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-design-jobs.rss',
    ]
    for feed_url in feeds:
        try:
            r = _req.get(feed_url, headers=_hdr(), timeout=12)
            if r.status_code != 200: continue
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:20]:
                title = (item.findtext('title') or '')
                link = (item.findtext('link') or '')
                desc = item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or item.findtext('description') or ''
                txt_clean = re.sub(r'<[^>]+>', ' ', f"{title} {desc}")
                emails, wa = _extract(txt_clean)
                if emails or wa:
                    leads.append({
                        'name': title.split('at ')[-1][:50] if ' at ' in title else title[:50],
                        'designation': _desig(title),
                        'email': emails[0] if emails else '',
                        'whatsapp': wa[0] if wa else '',
                        'source': 'weworkremotely',
                        'url': link,
                        'notes': title[:100],
                    })
        except Exception:
            continue
    return leads


def _fetch_github_jobs_rss() -> list[dict]:
    """GitHub discussions and community posts"""
    leads = []
    try:
        # GitHub explore feed
        r = _req.get(
            'https://api.github.com/search/issues?q=freelance+email+hire+label:hiring&sort=created&order=desc&per_page=30',
            headers={'Accept': 'application/vnd.github.v3+json'},
            timeout=12
        )
        if r.status_code != 200: return leads
        for issue in r.json().get('items', [])[:20]:
            txt = f"{issue.get('title','')} {issue.get('body','') or ''}"
            txt_clean = re.sub(r'<[^>]+>', ' ', txt)
            emails, wa = _extract(txt_clean)
            if emails or wa:
                leads.append({
                    'name': issue.get('user',{}).get('login',''),
                    'designation': _desig(issue.get('title','')),
                    'email': emails[0] if emails else '',
                    'whatsapp': wa[0] if wa else '',
                    'source': 'github',
                    'url': issue.get('html_url',''),
                    'notes': issue.get('title','')[:100],
                })
    except Exception:
        pass
    return leads


def _fetch_reddit_rss(subreddit: str) -> list[dict]:
    """Reddit via RSS — different from JSON API, often works"""
    leads = []
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit=50"
        hdrs = {
            'User-Agent': 'Mozilla/5.0 (compatible; RSS reader)',
            'Accept': 'application/rss+xml, application/xml, text/xml',
        }
        r = _req.get(url, headers=hdrs, timeout=15)
        if r.status_code != 200: return leads
        root = ET.fromstring(r.content)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }
        entries = root.findall('.//entry') or root.findall('.//item')
        for entry in entries[:30]:
            title = (
                (entry.find('atom:title', ns) or entry.find('title'))
            )
            title_txt = title.text if title is not None else ''
            content_el = (
                entry.find('content') or
                entry.find('atom:content', ns) or
                entry.find('{http://purl.org/rss/1.0/modules/content/}encoded')
            )
            body = content_el.text if content_el is not None else ''
            author_el = entry.find('atom:author/atom:name', ns) or entry.find('author')
            author = author_el.text if author_el is not None else ''
            link_el = entry.find('atom:link', ns) or entry.find('link')
            link = link_el.get('href','') if link_el is not None else ''
            txt_clean = re.sub(r'<[^>]+>', ' ', f"{title_txt} {body}")
            emails, wa = _extract(txt_clean)
            if emails or wa:
                leads.append({
                    'name': author,
                    'designation': _desig(title_txt),
                    'email': emails[0] if emails else '',
                    'whatsapp': wa[0] if wa else '',
                    'source': 'reddit',
                    'url': link,
                    'notes': title_txt[:100],
                })
    except Exception:
        pass
    return leads


# ── SOURCE 6: Public Portfolio Sites ────────────────────────────

def _fetch_carrd_profiles(keyword: str) -> list[dict]:
    """Carrd.co portfolio pages via Google search-like approach"""
    leads = []
    # These are already indexed public pages
    portfolio_urls = [
        f"https://dev.to/t/forhire",
        f"https://www.indiehackers.com/group/forhire",
    ]
    try:
        for url in portfolio_urls:
            r = _req.get(url, headers=_hdr(), timeout=12)
            if r.status_code != 200: continue
            soup = BeautifulSoup(r.text, 'html.parser')
            txt = soup.get_text(' ', strip=True)
            emails, wa = _extract(txt)
            for email in emails[:5]:
                leads.append({
                    'name': '',
                    'designation': 'Freelancer',
                    'email': email,
                    'whatsapp': wa[0] if wa else '',
                    'source': 'portfolio',
                    'url': url,
                    'notes': f'From {url}',
                })
    except Exception:
        pass
    return leads


# ── API Endpoints ─────────────────────────────────────────────────

GH_KEYWORDS = GH_SEARCH_QUERIES  # alias

@router.get("/api/scrape/test")
async def test_scraper():
    """Test which sources are accessible"""
    results = {}
    tests = [
        ('reddit_rss', 'https://www.reddit.com/r/forhire/new/.rss?limit=5', {'User-Agent':'Mozilla/5.0 (compatible; RSS)','Accept':'application/rss+xml'}),
        ('github', 'https://api.github.com/search/users?q=freelance+developer+email&per_page=3', {'Accept':'application/vnd.github.v3+json'}),
        ('devto', 'https://dev.to/api/articles?tag=forhire&per_page=3', {}),
        ('hackernews', 'https://hn.algolia.com/api/v1/search?query=freelancer&tags=story&hitsPerPage=3', {}),
        ('indiehackers', 'https://www.indiehackers.com/api/posts?limit=3', {}),
        ('remotive_rss', 'https://remotive.com/remote-jobs/feed', _hdr()),
        ('weworkremotely', 'https://weworkremotely.com/remote-jobs.rss', _hdr()),
    ]
    for name, url, hdrs in tests:
        try:
            r = _req.get(url, headers=hdrs, timeout=8)
            results[name] = {'status': r.status_code, 'ok': r.status_code == 200}
        except Exception as e:
            results[name] = {'status': 'error', 'error': str(e)[:60], 'ok': False}
    return JSONResponse(results)


@router.get("/api/scrape/platforms")
async def scrape_platforms():
    """212+ hunting platforms grouped by source type."""
    from app.services.lead_hunter_engine import list_platforms, summary

    return JSONResponse({"platforms": list_platforms(), "summary": summary()})


@router.get("/api/scrape/hunt-plan")
async def scrape_hunt_plan(chips: str = Query(default="github,reddit,devto,misc")):
    """Dynamic hunt plan for enabled UI chips."""
    from app.services.lead_hunter_engine import build_hunt_plan, summary

    enabled = [c.strip() for c in chips.split(",") if c.strip()]
    plan = build_hunt_plan(enabled)
    return JSONResponse({"plan": plan, "total_batches": sum(p["batches"] for p in plan), "summary": summary()})


@router.get("/api/scrape/registry")
async def scrape_registry(session: Annotated[Session, Depends(get_session)]):
    """Permanent hunted email/WhatsApp registry — never search these again."""
    from app.services.lead_hunter_registry import load_known_keys, registry_stats

    emails, whatsapps = load_known_keys(session)
    stats = registry_stats(session)
    return JSONResponse(
        {
            **stats,
            "emails": sorted(emails),
            "whatsapp": sorted(whatsapps),
        }
    )


@router.get("/api/scrape/leads")
async def scrape_leads(
    session: Annotated[Session, Depends(get_session)],
    target: str = Query(default="all"),
    keywords: str = Query(default=""),
    country: str = Query(default=""),
    batch_size: int = Query(default=50),
    source: str = Query(default="github"),
    offset: int = Query(default=0),
):
    """Server-side lead scraper — filters against permanent hunted registry."""
    from app.services.lead_hunter_engine import run_scrape_batch

    kw = keywords.strip()
    if country.strip():
        kw = f"{kw} {country.strip()}".strip()

    try:
        result = run_scrape_batch(session, source, offset, kw)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            {
                "leads": [],
                "count": 0,
                "source": source,
                "offset": offset,
                "skipped_known": 0,
                "registry_total": 0,
                "error": str(e),
            }
        )


@router.get("/api/license/status")
async def license_status_api(session: Annotated[Session, Depends(get_session)]):
    from app.services.license_service import license_status

    return JSONResponse(license_status(session))


@router.post("/api/license/activate")
async def license_activate_api(
    session: Annotated[Session, Depends(get_session)],
    key: str = Form(default=""),
):
    from app.services.license_service import activate_license

    return JSONResponse(activate_license(session, key))


@router.get("/api/scrape/export")
async def export_scraped_leads(
    fmt: str = Query(default="csv"),
    data: str = Query(default="[]"),
    filename: str = Query(default="leads"),
):
    """Export scraped leads in multiple formats"""
    try:
        leads = json.loads(data)
    except Exception:
        leads = []

    if not leads:
        raise HTTPException(status_code=400, detail="No leads to export")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[^\w\-]', '_', filename) or 'leads'
    fname = f"{safe_name}_{ts}"

    if fmt == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(['#','Name','Designation','Email','WhatsApp','Source','Profile URL','Notes'])
        for i, l in enumerate(leads, 1):
            w.writerow([i, l.get('name',''), l.get('designation',''), l.get('email',''), l.get('whatsapp',''), l.get('source',''), l.get('url',''), l.get('notes','')])
        out.seek(0)
        return StreamingResponse(
            iter([out.getvalue()]),
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{fname}.csv"'}
        )

    elif fmt == "json":
        return StreamingResponse(
            iter([json.dumps(leads, indent=2, ensure_ascii=False)]),
            media_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{fname}.json"'}
        )

    elif fmt == "txt_email":
        emails = '\n'.join(l.get('email','') for l in leads if l.get('email'))
        return StreamingResponse(
            iter([emails]),
            media_type='text/plain',
            headers={'Content-Disposition': f'attachment; filename="{fname}_emails.txt"'}
        )

    elif fmt == "txt_wa":
        wa_nums = '\n'.join(l.get('whatsapp','') for l in leads if l.get('whatsapp'))
        return StreamingResponse(
            iter([wa_nums]),
            media_type='text/plain',
            headers={'Content-Disposition': f'attachment; filename="{fname}_whatsapp.txt"'}
        )

    elif fmt in ("xls", "xlsx"):
        hdr = '<tr>' + ''.join(f'<th style="background:#7c3aed;color:white;padding:8px">{h}</th>' for h in ['#','Name','Designation','Email','WhatsApp','Source','Profile URL','Notes']) + '</tr>'
        rows = ''.join(
            f'<tr><td>{i}</td><td>{l.get("name","")}</td><td>{l.get("designation","")}</td>'
            f'<td>{l.get("email","")}</td><td>{l.get("whatsapp","")}</td>'
            f'<td>{l.get("source","")}</td><td>{l.get("url","")}</td><td>{l.get("notes","")}</td></tr>'
            for i, l in enumerate(leads, 1)
        )
        xls = f'<html><head><meta charset="UTF-8"></head><body><table border="1" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px">{hdr}{rows}</table></body></html>'
        return StreamingResponse(
            iter([xls]),
            media_type='application/vnd.ms-excel',
            headers={'Content-Disposition': f'attachment; filename="{fname}.xls"'}
        )

    elif fmt == "html":
        cards_parts = []
        for i, l in enumerate(leads, 1):
            email_html = ""
            if l.get("email"):
                email = l.get("email", "")
                email_html = (
                    f"<a href='mailto:{email}' style='color:#60a5fa;font-size:12px'>"
                    f"✉ {email}</a><br>"
                )
            wa_html = ""
            if l.get("whatsapp"):
                wa = l.get("whatsapp", "")
                wa_digits = wa.replace("+", "")
                wa_html = (
                    f"<a href='https://wa.me/{wa_digits}' style='color:#25d366;font-size:12px'>"
                    f"💬 {wa}</a><br>"
                )
            cards_parts.append(
                f'<div style="border:1px solid #7c3aed;border-radius:10px;padding:16px;margin:8px;'
                f'display:inline-block;min-width:240px;max-width:300px;background:#0e0e1c;color:#eeeef8;'
                f'vertical-align:top;font-family:sans-serif">'
                f'<div style="font-weight:700;font-size:14px;margin-bottom:4px">#{i} {l.get("name", "Unknown")}</div>'
                f'<div style="font-size:11px;color:#a07cfc;margin-bottom:8px">{l.get("designation", "")}</div>'
                f'{email_html}{wa_html}'
                f'<div style="font-size:10px;color:#6666a0;margin-top:6px">{l.get("source", "")}</div>'
                f'</div>'
            )
        cards = "".join(cards_parts)
        html_out = (
            f'<!DOCTYPE html><html><head><meta charset="UTF-8">'
            f'<title>Lead Hunter — {len(leads)} Contacts</title>'
            f'<style>body{{background:#080812;padding:24px;font-family:sans-serif}}'
            f'h2{{color:#c084fc;margin-bottom:20px}}'
            f'.stats{{color:#6666a0;font-size:13px;margin-bottom:20px}}</style></head>'
            f'<body><h2>🎯 Lead Hunter Pro — {len(leads)} Contacts</h2>'
            f'<div class="stats">Generated: {datetime.now().strftime("%d %b %Y %H:%M")} | '
            f'Emails: {sum(1 for l in leads if l.get("email"))} | '
            f'WhatsApp: {sum(1 for l in leads if l.get("whatsapp"))}</div>'
            f'{cards}</body></html>'
        )
        return StreamingResponse(
            iter([html_out]),
            media_type='text/html',
            headers={'Content-Disposition': f'attachment; filename="{fname}.html"'}
        )

    raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}. Use: csv, json, xls, xlsx, txt_email, txt_wa, html")