from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import ApplicationRecord
from app.routes.web import compose_notes, extract_follow_up_date, strip_follow_up_marker

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    candidate_id: int
    job_title: str
    company: str
    source: str
    job_url: str
    status: str = "saved"
    notes: str = ""
    follow_up_date: str = ""


class ApplicationUpdate(BaseModel):
    status: str
    notes: str = ""
    follow_up_date: str = ""


@router.post("/")
def create_application(payload: ApplicationCreate, session: Annotated[Session, Depends(get_session)]):
    data = payload.model_dump()
    follow_up_date = data.pop("follow_up_date", "")
    data["notes"] = compose_notes(data.get("notes", ""), follow_up_date)
    row = ApplicationRecord(**data)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        **row.model_dump(),
        "notes": strip_follow_up_marker(row.notes),
        "follow_up_date": extract_follow_up_date(row.notes),
    }


@router.get("/{candidate_id}")
def list_applications(candidate_id: int, session: Annotated[Session, Depends(get_session)]):
    statement = (
        select(ApplicationRecord)
        .where(ApplicationRecord.candidate_id == candidate_id)
        .order_by(ApplicationRecord.updated_at.desc())
    )
    rows = session.exec(statement).all()
    return [
        {
            **row.model_dump(),
            "notes": strip_follow_up_marker(row.notes),
            "follow_up_date": extract_follow_up_date(row.notes),
        }
        for row in rows
    ]


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
    row.notes = compose_notes(payload.notes, payload.follow_up_date)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        **row.model_dump(),
        "notes": strip_follow_up_marker(row.notes),
        "follow_up_date": extract_follow_up_date(row.notes),
    }
