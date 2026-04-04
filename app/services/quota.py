from datetime import datetime

from sqlmodel import Session, select

from app.config import settings
from app.models import CandidateProfile, UsageCounter


def current_period() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_or_create_usage(session: Session, candidate_id: int) -> UsageCounter:
    period = current_period()
    statement = select(UsageCounter).where(
        UsageCounter.candidate_id == candidate_id,
        UsageCounter.period == period,
    )
    usage = session.exec(statement).first()
    if usage:
        return usage

    usage = UsageCounter(candidate_id=candidate_id, period=period, matches_used=0)
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return usage


def ensure_can_consume_matches(session: Session, candidate: CandidateProfile, needed: int) -> None:
    if candidate.is_premium:
        return

    usage = get_or_create_usage(session, candidate.id)
    if usage.matches_used + needed > settings.free_monthly_match_limit:
        raise ValueError(
            "Free monthly match limit reached. Upgrade via self-hosting/BYO keys for unlimited usage."
        )


def consume_matches(session: Session, candidate: CandidateProfile, consumed: int) -> UsageCounter:
    usage = get_or_create_usage(session, candidate.id)
    if not candidate.is_premium:
        usage.matches_used += consumed
        session.add(usage)
        session.commit()
        session.refresh(usage)
    return usage
