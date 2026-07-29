"""Persistent hunted contact registry — emails/WhatsApp never searched again."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Iterable

from sqlmodel import Session, select

from app.models import DoNotContactEntry, HuntedContact, HuntSession

logger = logging.getLogger("jobmind.leadhunter.registry")

_EMAILS_ALL_TIME_FILENAME = "emails_all_time.txt"
_WHATSAPP_ALL_TIME_FILENAME = "whatsapp_all_time.txt"


def _append_all_time(email: str, whatsapp: str) -> None:
    """Appends a newly-registered contact to the cumulative all-time export
    files, in the app's own data directory (next to the database — never
    Downloads). Only called for genuinely new HuntedContact rows, and
    HuntedContact is itself the permanent dedup registry, so every call here
    is already guaranteed unique — no need to re-read the file to dedupe.
    Best-effort: a write failure here must never break a hunt batch, it just
    means this session's contacts are still on the file for next time."""
    if not email and not whatsapp:
        return
    from app.paths import data_dir

    try:
        directory = data_dir()
        directory.mkdir(parents=True, exist_ok=True)
        if email:
            with open(directory / _EMAILS_ALL_TIME_FILENAME, "a", encoding="utf-8") as fh:
                fh.write(email + "\n")
        if whatsapp:
            with open(directory / _WHATSAPP_ALL_TIME_FILENAME, "a", encoding="utf-8") as fh:
                fh.write(whatsapp + "\n")
    except OSError:
        logger.exception("registry: failed to append to all-time contact files")


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


def _norm_whatsapp(value: str) -> str:
    raw = re.sub(r"[^\d+]", "", (value or "").strip())
    if raw and not raw.startswith("+"):
        raw = "+" + raw
    return raw


def load_known_keys(session: Session) -> tuple[set[str], set[str]]:
    emails: set[str] = set()
    whatsapps: set[str] = set()
    for row in session.exec(select(HuntedContact)).all():
        email = _norm_email(row.email)
        wa = _norm_whatsapp(row.whatsapp)
        if email:
            emails.add(email)
        if wa:
            whatsapps.add(wa)
    return emails, whatsapps


def load_dnc_keys(session: Session) -> tuple[set[str], set[str]]:
    """Emails/WhatsApp numbers the user has opted out of contacting again."""
    emails: set[str] = set()
    whatsapps: set[str] = set()
    for row in session.exec(select(DoNotContactEntry)).all():
        email = _norm_email(row.email)
        wa = _norm_whatsapp(row.whatsapp)
        if email:
            emails.add(email)
        if wa:
            whatsapps.add(wa)
    return emails, whatsapps


def filter_new_leads(
    leads: list[dict],
    known_emails: set[str],
    known_whatsapp: set[str],
) -> tuple[list[dict], int]:
    fresh: list[dict] = []
    skipped = 0
    for lead in leads:
        email = _norm_email(lead.get("email", ""))
        wa = _norm_whatsapp(lead.get("whatsapp", ""))
        if not email and not wa:
            skipped += 1
            continue
        if email and email in known_emails:
            skipped += 1
            continue
        if wa and wa in known_whatsapp:
            skipped += 1
            continue
        if wa and not email and wa in known_whatsapp:
            skipped += 1
            continue
        fresh.append(lead)
        if email:
            known_emails.add(email)
        if wa:
            known_whatsapp.add(wa)
    return fresh, skipped


def register_leads(session: Session, leads: Iterable[dict], hunt_session_id: int | None = None) -> int:
    saved = 0
    for lead in leads:
        email = _norm_email(lead.get("email", ""))
        wa = _norm_whatsapp(lead.get("whatsapp", ""))
        if not email and not wa:
            continue
        existing = None
        if email:
            existing = session.exec(
                select(HuntedContact).where(HuntedContact.email == email)
            ).first()
        if not existing and wa:
            existing = session.exec(
                select(HuntedContact).where(HuntedContact.whatsapp == wa)
            ).first()
        source = (lead.get("source") or "")[:80]
        if existing:
            # Not a new contact, but a 2nd (or 3rd...) independent sighting
            # is itself a confidence signal — cross-source confirmation is
            # stronger evidence than any single source's own discovery
            # method, so this elevates the tier even for a contact first
            # found via a lower-confidence text-pattern match.
            seen = [s for s in existing.seen_sources.split(",") if s]
            if source and source not in seen:
                seen.append(source)
                existing.seen_sources = ",".join(seen)
                if len(seen) >= 2:
                    existing.confidence = "high"
                session.add(existing)
                session.commit()
            continue
        session.add(
            HuntedContact(
                email=email,
                whatsapp=wa,
                name=(lead.get("name") or "")[:120],
                designation=(lead.get("designation") or "")[:120],
                source=source,
                url=(lead.get("url") or "")[:500],
                notes=(lead.get("notes") or "")[:300],
                location=(lead.get("location") or "")[:120],
                hunt_session_id=hunt_session_id,
                hunted_at=datetime.utcnow(),
                confidence=lead.get("confidence") or "medium",
                discovery_method=lead.get("discovery_method") or "text_pattern",
                seen_sources=source,
            )
        )
        saved += 1
        _append_all_time(email, wa)
        # Commit each contact as it's found rather than batching until the
        # whole source finishes — if the app is killed mid-hunt, everything
        # found so far must already be on disk.
        session.commit()
    return saved


def registry_stats(session: Session) -> dict:
    rows = session.exec(select(HuntedContact)).all()
    return {
        "total": len(rows),
        "emails": sum(1 for row in rows if row.email),
        "whatsapp": sum(1 for row in rows if row.whatsapp),
    }


def _contact_to_dict(row: HuntedContact) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "designation": row.designation,
        "email": row.email,
        "whatsapp": row.whatsapp,
        "source": row.source,
        "url": row.url,
        "notes": row.notes,
        "location": row.location,
        "hunted_at": row.hunted_at.isoformat(),
        "confidence": row.confidence,
        "discovery_method": row.discovery_method,
        "seen_sources": row.seen_sources,
    }


def start_hunt_session(
    session: Session,
    candidate_id: int = 0,
    target: str = "",
    keywords: str = "",
    location: str = "",
    chips_csv: str = "",
) -> HuntSession:
    hunt_session = HuntSession(
        candidate_id=candidate_id,
        target=target,
        keywords=keywords,
        location=location,
        chips_csv=chips_csv,
        status="running",
    )
    session.add(hunt_session)
    session.commit()
    session.refresh(hunt_session)
    return hunt_session


def end_hunt_session(session: Session, hunt_session_id: int, status: str = "completed") -> HuntSession | None:
    hunt_session = session.get(HuntSession, hunt_session_id)
    if not hunt_session:
        return None
    hunt_session.status = status
    hunt_session.ended_at = datetime.utcnow()
    session.add(hunt_session)
    session.commit()
    session.refresh(hunt_session)
    return hunt_session


def get_session_leads(session: Session, hunt_session_id: int) -> list[dict]:
    rows = session.exec(
        select(HuntedContact)
        .where(HuntedContact.hunt_session_id == hunt_session_id)
        .order_by(HuntedContact.hunted_at)
    ).all()
    return [_contact_to_dict(row) for row in rows]


def pool_health(session: Session) -> dict:
    """What 'maximum hunting' actually looks like day to day: not one big
    hunt, but a steadily growing, deduplicated pool. Cheap enough to compute
    on every dashboard load — HuntedContact stays in the low tens of
    thousands even for a heavily-used install, well within a single
    in-memory pass."""
    now = datetime.utcnow()
    rows = session.exec(select(HuntedContact)).all()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    high = sum(1 for r in rows if r.confidence == "high")
    return {
        "total": len(rows),
        "growth_7d": sum(1 for r in rows if r.hunted_at >= cutoff_7d),
        "growth_30d": sum(1 for r in rows if r.hunted_at >= cutoff_30d),
        "confidence_high": high,
        "confidence_medium": len(rows) - high,
        "emails": sum(1 for r in rows if r.email),
        "whatsapp": sum(1 for r in rows if r.whatsapp),
    }


def list_hunt_sessions(session: Session, limit: int = 100) -> list[dict]:
    """Every past hunt session, newest first, with per-session contact
    counts — the query behind the Hunt History view. All the data already
    exists (HuntSession + HuntedContact.hunt_session_id from the Priority-0
    persistence work); this is just a read, no new scraping."""
    sessions = session.exec(
        select(HuntSession).order_by(HuntSession.started_at.desc()).limit(limit)
    ).all()
    result: list[dict] = []
    for hunt_session in sessions:
        contacts = session.exec(
            select(HuntedContact).where(HuntedContact.hunt_session_id == hunt_session.id)
        ).all()
        result.append(
            {
                "id": hunt_session.id,
                "status": hunt_session.status,
                "target": hunt_session.target,
                "keywords": hunt_session.keywords,
                "location": hunt_session.location,
                "chips_csv": hunt_session.chips_csv,
                "started_at": hunt_session.started_at.isoformat(),
                "ended_at": hunt_session.ended_at.isoformat() if hunt_session.ended_at else None,
                "lead_count": len(contacts),
                "email_count": sum(1 for c in contacts if c.email),
                "whatsapp_count": sum(1 for c in contacts if c.whatsapp),
            }
        )
    return result


def get_latest_session(session: Session) -> dict | None:
    hunt_session = session.exec(
        select(HuntSession).order_by(HuntSession.started_at.desc())
    ).first()
    if not hunt_session:
        return None
    lead_count = len(
        session.exec(
            select(HuntedContact).where(HuntedContact.hunt_session_id == hunt_session.id)
        ).all()
    )
    return {
        "id": hunt_session.id,
        "status": hunt_session.status,
        "target": hunt_session.target,
        "keywords": hunt_session.keywords,
        "location": hunt_session.location,
        "started_at": hunt_session.started_at.isoformat(),
        "ended_at": hunt_session.ended_at.isoformat() if hunt_session.ended_at else None,
        "lead_count": lead_count,
    }
