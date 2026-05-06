from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class CandidateProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str
    skills_csv: str = ""
    github_username: str = ""
    resume_url: str = ""
    portfolio_url: str = ""
    linkedin_url: str = ""
    upwork_url: str = ""
    fiverr_url: str = ""
    product_name: str = ""
    product_url: str = ""
    sales_pitch: str = ""
    cv_text: str = ""
    is_premium: bool = False


class JobListing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    title: str
    company: str
    location: str = "Remote"
    url: str
    description: str


class MatchScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int
    job_id: int
    score: float
    reason: str = ""


class UsageCounter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int
    period: str
    matches_used: int = 0


class ApplicationRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int
    job_title: str
    company: str
    source: str
    job_url: str
    status: str = "saved"
    notes: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClientLead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int
    lead_name: str = ""
    company: str
    source: str
    lead_url: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    contact_channel: str = "email"
    offer_type: str = "services"
    status: str = "new"
    notes: str = ""
    follow_up_date: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FilterPreset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int
    name: str
    preset_json: str = "{}"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
