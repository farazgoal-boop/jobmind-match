"""Persistent hunted contact registry — emails/WhatsApp never searched again."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from sqlmodel import Session, select

from app.models import HuntedContact


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


def register_leads(session: Session, leads: Iterable[dict]) -> int:
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
        if existing:
            continue
        session.add(
            HuntedContact(
                email=email,
                whatsapp=wa,
                name=(lead.get("name") or "")[:120],
                designation=(lead.get("designation") or "")[:120],
                source=(lead.get("source") or "")[:80],
                url=(lead.get("url") or "")[:500],
                notes=(lead.get("notes") or "")[:300],
                hunted_at=datetime.utcnow(),
            )
        )
        saved += 1
    if saved:
        session.commit()
    return saved


def registry_stats(session: Session) -> dict:
    rows = session.exec(select(HuntedContact)).all()
    return {
        "total": len(rows),
        "emails": sum(1 for row in rows if row.email),
        "whatsapp": sum(1 for row in rows if row.whatsapp),
    }
