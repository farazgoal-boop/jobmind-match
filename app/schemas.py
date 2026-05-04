from pydantic import BaseModel, EmailStr


class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    skills_csv: str = ""
    github_username: str = ""
    resume_url: str = ""
    portfolio_url: str = ""


class CandidateOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    skills_csv: str
    github_username: str
    resume_url: str
    portfolio_url: str


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    source: str
    url: str


class MatchOut(BaseModel):
    job_id: int
    title: str
    company: str
    score: float
    reason: str
