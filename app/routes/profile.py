from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

from app.db import get_session
from app.models import CandidateProfile
from app.schemas import CandidateCreate
from app.services.cv_parser import (
    extract_sections,
    extract_technologies,
    extract_text_from_docx,
    extract_text_from_pdf,
)
from app.services.github_client import fetch_repo_insights

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/")
def create_profile(payload: CandidateCreate, session: Annotated[Session, Depends(get_session)]):
    profile = CandidateProfile(**payload.model_dump())
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.post("/{candidate_id}/upload-cv")
async def upload_cv(
    candidate_id: int,
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
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are supported")

    profile.cv_text = cv_text
    session.add(profile)
    session.commit()

    sections = extract_sections(cv_text)
    tech = extract_technologies(cv_text)
    return {"sections": sections, "technologies": tech}


@router.get("/{candidate_id}/github")
def github_summary(candidate_id: int, session: Annotated[Session, Depends(get_session)]):
    profile = session.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return fetch_repo_insights(profile.github_username)
