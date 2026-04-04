from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.models import CandidateProfile
from app.services.matcher import rank_jobs
from app.services.quota import consume_matches, ensure_can_consume_matches
from app.services.source_registry import fetch_jobs_from_sources, free_sources_list

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/sources")
def get_jobs_by_source(sources: str = "remotive,weworkremotely", limit_per_source: int = 20):
    source_list = [s.strip().lower() for s in sources.split(",") if s.strip()]
    return fetch_jobs_from_sources(source_list, limit_per_source=limit_per_source)


@router.get("/match/{candidate_id}")
def get_matches(
    candidate_id: int,
    top_k: int = 5,
    sources: str = "",
    session: Annotated[Session, Depends(get_session)] = None,
):
    profile = session.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if profile.id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")

    selected_sources = [s.strip().lower() for s in sources.split(",") if s.strip()] or free_sources_list()

    if not profile.is_premium:
        selected_sources = selected_sources[:2]

    jobs = fetch_jobs_from_sources(selected_sources, limit_per_source=80)
    candidate_text = " ".join([profile.skills_csv, profile.cv_text])
    matches = rank_jobs(candidate_text=candidate_text, jobs=jobs, top_k=top_k)

    try:
        ensure_can_consume_matches(session, profile, len(matches))
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    usage = consume_matches(session, profile, len(matches))
    return {
        "matches": matches,
        "period": usage.period,
        "matches_used": usage.matches_used,
        "monthly_limit": None if profile.is_premium else settings.free_monthly_match_limit,
        "sources_used": selected_sources,
    }
