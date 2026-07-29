"""Background/scheduled hunting: discovery has no daily ceiling, so this
turns "click Start Hunting" from the only way to grow the contact pool into
one of several — the scheduler now also grows it continuously, a few
platforms at a time, rotating through the full platform list so the same
sources never get hit back-to-back.

This module is deliberately just orchestration around functions that
already exist and are already tested: run_scrape_batch does the actual
fetch + Pass 2 crawl + DNC filter + confidence tagging (lead_hunter_engine.py),
start_hunt_session/end_hunt_session track it as a real HuntSession
(lead_hunter_registry.py) so it shows up in Hunt History like any other
hunt. Nothing about contact discovery/filtering is reimplemented here.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlmodel import Session

from app.models import AppSetting
from app.services.lead_platforms import PLATFORMS

logger = logging.getLogger("jobmind.leadhunter.autohunt")

_ENABLED_KEY = "auto_hunt_enabled"
_INTERVAL_HOURS_KEY = "auto_hunt_interval_hours"
_CURSOR_KEY = "auto_hunt_cursor"
_SESSION_ID_KEY = "auto_hunt_session_id"
_LAST_RUN_KEY = "auto_hunt_last_run_at"

DEFAULT_INTERVAL_HOURS = 4
# How many platforms one tick advances through. Each one still goes through
# run_scrape_batch's own ~25s Pass 1 timeout + ~15s Pass 2 crawl budget, so
# this bounds a single tick to roughly N * 40s worst case — comfortably
# under the scheduler's own polling interval (see scheduler.py), so ticks
# can't stack up on each other even in the worst case.
PLATFORMS_PER_TICK = 5


def _get(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppSetting, key)
    return row.value if row else default


def _set(session: Session, key: str, value: str) -> None:
    session.merge(AppSetting(key=key, value=value))
    session.commit()


def get_auto_hunt_settings(session: Session) -> dict:
    return {
        "enabled": _get(session, _ENABLED_KEY) == "1",
        "interval_hours": int(_get(session, _INTERVAL_HOURS_KEY, str(DEFAULT_INTERVAL_HOURS)) or DEFAULT_INTERVAL_HOURS),
        "last_run_at": _get(session, _LAST_RUN_KEY, "") or None,
        "cursor": int(_get(session, _CURSOR_KEY, "0") or 0),
        "platforms_per_tick": PLATFORMS_PER_TICK,
        "total_platforms": len(PLATFORMS),
    }


def set_auto_hunt_settings(session: Session, enabled: bool, interval_hours: int) -> dict:
    interval_hours = max(1, min(interval_hours, 24))
    _set(session, _ENABLED_KEY, "1" if enabled else "")
    _set(session, _INTERVAL_HOURS_KEY, str(interval_hours))
    return get_auto_hunt_settings(session)


def _next_platform_batch(session: Session) -> list[dict]:
    """The next PLATFORMS_PER_TICK platforms after the persisted cursor,
    wrapping around — a full rotation eventually touches every platform
    instead of the same handful every tick."""
    cursor = int(_get(session, _CURSOR_KEY, "0") or 0)
    total = len(PLATFORMS)
    if total == 0:
        return []
    batch = [PLATFORMS[(cursor + i) % total] for i in range(min(PLATFORMS_PER_TICK, total))]
    _set(session, _CURSOR_KEY, str((cursor + len(batch)) % total))
    return batch


def _get_or_create_background_session(session: Session) -> int:
    from app.services.lead_hunter_registry import start_hunt_session

    existing_id = _get(session, _SESSION_ID_KEY, "")
    if existing_id:
        from app.models import HuntSession

        hunt_session = session.get(HuntSession, int(existing_id))
        if hunt_session and hunt_session.status == "running":
            return hunt_session.id

    hunt_session = start_hunt_session(
        session, target="sell", keywords="", location="", chips_csv="auto-hunt"
    )
    _set(session, _SESSION_ID_KEY, str(hunt_session.id))
    return hunt_session.id


def run_auto_hunt_tick() -> dict:
    """Called on every scheduler poll (see scheduler.py) — cheap no-op
    unless auto-hunt is enabled AND the configured interval has actually
    elapsed since the last real run. Never raises: a single tick failing
    (network blip, a source erroring) must not take down the scheduler or
    block the next tick."""
    from app.db import engine
    from app.services.lead_hunter_engine import run_scrape_batch

    summary = {"ran": False, "reason": "", "platforms": [], "fresh_total": 0}
    try:
        with Session(engine) as session:
            cfg = get_auto_hunt_settings(session)
            if not cfg["enabled"]:
                summary["reason"] = "disabled"
                return summary

            last_run_at = cfg["last_run_at"]
            if last_run_at:
                elapsed = datetime.utcnow() - datetime.fromisoformat(last_run_at)
                if elapsed < timedelta(hours=cfg["interval_hours"]):
                    summary["reason"] = "not due yet"
                    return summary

            batch = _next_platform_batch(session)
            if not batch:
                summary["reason"] = "no platforms configured"
                return summary

            hunt_session_id = _get_or_create_background_session(session)
            fresh_total = 0
            for platform in batch:
                try:
                    result = run_scrape_batch(
                        session, platform["id"], offset=0, hunt_session_id=hunt_session_id
                    )
                    fresh_total += result.get("count", 0)
                    summary["platforms"].append({"source": platform["id"], "fresh": result.get("count", 0), "error": result.get("error", "")})
                except Exception:
                    logger.exception("auto-hunt: platform %s raised", platform["id"])
                    summary["platforms"].append({"source": platform["id"], "fresh": 0, "error": "raised"})

            _set(session, _LAST_RUN_KEY, datetime.utcnow().isoformat())
            summary["ran"] = True
            summary["fresh_total"] = fresh_total
            logger.info(
                "auto-hunt: tick ran %d platforms, %d fresh contacts, session=%s",
                len(batch), fresh_total, hunt_session_id,
            )
            return summary
    except Exception:
        logger.exception("auto-hunt: tick failed")
        summary["reason"] = "tick error"
        return summary
