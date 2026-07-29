"""Unit tests for the hunt-session persistence layer: every contact found
must be on disk immediately, and still be there — queryable by session —
after the process that found it is gone."""
from sqlmodel import Session

from app.services.lead_hunter_registry import (
    end_hunt_session,
    get_latest_session,
    get_session_leads,
    register_leads,
    start_hunt_session,
)


def _fake_lead(i: int) -> dict:
    return {
        "name": f"Contact {i}",
        "designation": "Freelance Developer",
        "email": f"contact{i}@example.com",
        "whatsapp": "",
        "source": "github",
        "url": f"https://github.com/contact{i}",
        "notes": "found during test hunt",
        "location": "Remote",
    }


def test_register_leads_tags_and_commits_per_contact(db_session: Session, fresh_engine):
    hunt_session = start_hunt_session(db_session, target="sell", keywords="python", location="Remote")
    assert hunt_session.id is not None
    assert hunt_session.status == "running"

    saved = register_leads(db_session, [_fake_lead(1), _fake_lead(2)], hunt_session_id=hunt_session.id)
    assert saved == 2

    # Simulate the app being killed right here, before the hunt ever
    # finishes or calls session/end — a brand-new connection to the same
    # file must already see both contacts.
    with Session(fresh_engine) as restarted_session:
        leads = get_session_leads(restarted_session, hunt_session.id)
        assert {l["email"] for l in leads} == {"contact1@example.com", "contact2@example.com"}


def test_get_latest_session_reports_unfinished_run(db_session: Session, fresh_engine):
    hunt_session = start_hunt_session(db_session, target="job", keywords="", location="")
    register_leads(db_session, [_fake_lead(101)], hunt_session_id=hunt_session.id)
    # No end_hunt_session call — this run "crashed" mid-hunt.

    with Session(fresh_engine) as restarted_session:
        latest = get_latest_session(restarted_session)
        assert latest is not None
        assert latest["id"] == hunt_session.id
        assert latest["status"] == "running"
        assert latest["lead_count"] == 1


def test_end_hunt_session_updates_status(db_session: Session):
    hunt_session = start_hunt_session(db_session, target="job")
    ended = end_hunt_session(db_session, hunt_session.id, status="stopped")
    assert ended is not None
    assert ended.status == "stopped"
    assert ended.ended_at is not None


def test_dedup_still_applies_across_sessions(db_session: Session):
    """A contact already hunted in a previous session must not be re-savable
    under a new session — the permanent registry guarantee must survive the
    new hunt_session_id column."""
    s1 = start_hunt_session(db_session, target="job")
    assert register_leads(db_session, [_fake_lead(500)], hunt_session_id=s1.id) == 1

    s2 = start_hunt_session(db_session, target="job")
    assert register_leads(db_session, [_fake_lead(500)], hunt_session_id=s2.id) == 0
    assert get_session_leads(db_session, s2.id) == []
