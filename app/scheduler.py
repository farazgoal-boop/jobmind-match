import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import CandidateProfile
from app.services.matcher import rank_jobs
from app.services.notifier import send_email_digest
from app.services.source_registry import fetch_jobs_from_sources, free_sources_list

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_daily_digest() -> None:
    with Session(engine) as session:
        candidates = session.exec(select(CandidateProfile)).all()

        for candidate in candidates:
            if not candidate.email:
                continue

            try:
                selected_sources = (
                    free_sources_list()
                    if not candidate.is_premium
                    else [s.strip().lower() for s in settings.premium_sources.split(",") if s.strip()]
                )
                jobs = fetch_jobs_from_sources(selected_sources, limit_per_source=60)
                candidate_text = " ".join([candidate.skills_csv, candidate.cv_text])
                matches = rank_jobs(candidate_text, jobs, top_k=settings.daily_digest_top_k)
                if matches:
                    send_email_digest(candidate.email, matches)
            except Exception as exc:
                logger.warning("Daily digest failed for candidate %s: %s", candidate.id, exc)


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_daily_digest,
        trigger="cron",
        hour=settings.daily_digest_hour,
        minute=0,
        id="daily-digest",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
