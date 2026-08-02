"""Unit tests for app.services.quota — free-tier monthly match limit enforcement."""
import pytest
from sqlmodel import Session

from app.config import settings
from app.models import CandidateProfile
from app.services.quota import consume_matches, ensure_can_consume_matches, get_or_create_usage


def _candidate(db_session: Session, is_premium: bool = False) -> CandidateProfile:
    candidate = CandidateProfile(full_name="Quota Test", email=f"quota-{id(object())}@example.com", is_premium=is_premium)
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def test_get_or_create_usage_starts_at_zero(db_session: Session):
    candidate = _candidate(db_session)
    usage = get_or_create_usage(db_session, candidate.id)
    assert usage.matches_used == 0
    assert usage.candidate_id == candidate.id


def test_ensure_can_consume_matches_raises_once_limit_exceeded(db_session: Session):
    candidate = _candidate(db_session)
    consume_matches(db_session, candidate, settings.free_monthly_match_limit)

    with pytest.raises(ValueError):
        ensure_can_consume_matches(db_session, candidate, 1)


def test_ensure_can_consume_matches_allows_up_to_the_limit(db_session: Session):
    candidate = _candidate(db_session)
    # Should not raise.
    ensure_can_consume_matches(db_session, candidate, settings.free_monthly_match_limit)


def test_premium_candidate_bypasses_limit_entirely(db_session: Session):
    candidate = _candidate(db_session, is_premium=True)
    consume_matches(db_session, candidate, settings.free_monthly_match_limit + 50)
    # No raise even though a free candidate would already be over limit.
    ensure_can_consume_matches(db_session, candidate, 1000)


def test_consume_matches_increments_usage_for_free_candidate(db_session: Session):
    candidate = _candidate(db_session)
    usage = consume_matches(db_session, candidate, 3)
    assert usage.matches_used == 3
    usage = consume_matches(db_session, candidate, 2)
    assert usage.matches_used == 5


def test_consume_matches_does_not_increment_for_premium_candidate(db_session: Session):
    candidate = _candidate(db_session, is_premium=True)
    usage = consume_matches(db_session, candidate, 5)
    assert usage.matches_used == 0
