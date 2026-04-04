from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import ApplicationRecord

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    candidate_id: int
    job_title: str
    company: str
    source: str
    job_url: str
    status: str = "saved"
    notes: str = ""


class ApplicationUpdate(BaseModel):
    status: str
    notes: str = ""


@router.post("/")
def create_application(payload: ApplicationCreate, session: Annotated[Session, Depends(get_session)]):
    row = ApplicationRecord(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/{candidate_id}")
def list_applications(candidate_id: int, session: Annotated[Session, Depends(get_session)]):
    statement = (
        select(ApplicationRecord)
        .where(ApplicationRecord.candidate_id == candidate_id)
        .order_by(ApplicationRecord.updated_at.desc())
    )
    return session.exec(statement).all()


@router.patch("/{application_id}")
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    row = session.get(ApplicationRecord, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    row.status = payload.status
    row.notes = payload.notes
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
