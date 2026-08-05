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


# Local-parts that show up constantly in blog posts, READMEs, and bios as
# example/placeholder text rather than a real person's address — syntax- and
# MX-valid (the domain is genuine), but obviously not a contactable person.
# Only flagged on a generic free-mail domain: "admin@company.com" or
# "contact@company.com" is often a real role account, but the same local
# part on gmail.com/yahoo.com/etc is almost always leftover placeholder text.
_PLACEHOLDER_LOCAL_PARTS = {
    "example", "test", "admin", "user", "name", "email", "contact",
    "your_email", "youremail", "someone", "info", "sample", "demo",
    "yourname", "firstname", "lastname", "johndoe", "janedoe",
    "test123", "email123", "noone", "nobody",
}

_FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "protonmail.com", "live.com", "msn.com", "mail.com",
    "yandex.com", "gmx.com", "zoho.com",
}

_SHORT_LETTERS = re.compile(r"^[a-z]{1,2}$")

# Same reserved-TLD family as web.py's _RESERVED_TLDS (RFC 2606 test/example/
# invalid/localhost + RFC 6762's .local for mDNS/link-local) -- duplicated
# here rather than imported since web.py imports FROM this module, and
# registry rows collected before a TLD was added to that hard-reject filter
# can still be sitting in the DB at medium/high. Lets
# reclassify_placeholder_confidence() sweep those out to "low" without
# deleting them.
_RESERVED_TLDS = {"test", "example", "invalid", "localhost", "local"}


def is_placeholder_email(email: str) -> bool:
    """True for obvious placeholder/example addresses that pass syntax and
    MX checks (the domain is real) but are plainly not a real contact — e.g.
    "a@b.com", "your_email@gmail.com", "admin@gmail.com", or an address on a
    reserved TLD like "user@host.local" (never real, routable mail).
    Deliberately a pattern list, not exhaustive — pairs with the "low"
    confidence tier rather than dropping matches outright, since some will
    be real people.

    A short (1-2 letter) local-part is NOT flagged by itself — that's a
    common, legitimate convention for people who own their own short domain
    (m@morgante.net, k@kay.is, hn@turbines.io are all real addresses seen in
    this registry). It's only a placeholder signal when the domain name is
    *also* reduced to 1-2 letters ("a@b.com", "x@yz.com") — that combination
    is the actual signature of hand-typed example text, not a real domain
    owner's short address."""
    local, _, domain = (email or "").strip().lower().partition("@")
    if not local or not domain:
        return False
    sld = domain.split(".", 1)[0]
    if _SHORT_LETTERS.match(local) and _SHORT_LETTERS.match(sld):
        return True
    if local in _PLACEHOLDER_LOCAL_PARTS and domain in _FREE_MAIL_DOMAINS:
        return True
    if domain.rsplit(".", 1)[-1] in _RESERVED_TLDS:
        return True
    return False


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
                # A junk placeholder address seen on 2 sources is still junk
                # (both sightings are probably the same copy-pasted example
                # text) — don't let cross-source confirmation launder it
                # into "high".
                if len(seen) >= 2 and not is_placeholder_email(existing.email):
                    existing.confidence = "high"
                session.add(existing)
                session.commit()
            continue
        confidence = "low" if email and is_placeholder_email(email) else (lead.get("confidence") or "medium")
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
                confidence=confidence,
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


def reclassify_placeholder_confidence(session: Session, dry_run: bool = False) -> list[dict]:
    """One-time cleanup pass: existing registry rows predate the placeholder
    check in register_leads(), so this re-classifies any of them matching
    is_placeholder_email() to "low" confidence. Never deletes rows — a
    flagged contact might still be real, it's just marked as unverified/risky
    rather than silently sitting at medium alongside genuinely good contacts.
    Idempotent: re-running it after the first pass is a no-op (already-"low"
    rows are skipped). Returns the list of rows changed (or, with
    dry_run=True, that *would* change) as plain dicts for reporting."""
    changed: list[dict] = []
    rows = session.exec(select(HuntedContact)).all()
    for row in rows:
        if row.confidence == "low":
            continue
        if row.email and is_placeholder_email(row.email):
            changed.append(_contact_to_dict(row))
            if not dry_run:
                row.confidence = "low"
                session.add(row)
    if not dry_run and changed:
        session.commit()
    return changed


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
    low = sum(1 for r in rows if r.confidence == "low")
    return {
        "total": len(rows),
        "growth_7d": sum(1 for r in rows if r.hunted_at >= cutoff_7d),
        "growth_30d": sum(1 for r in rows if r.hunted_at >= cutoff_30d),
        "confidence_high": high,
        "confidence_medium": len(rows) - high - low,
        "confidence_low": low,
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
