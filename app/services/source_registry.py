from typing import Dict, List

from app.config import settings
from app.services.job_sources.arbeitnow import fetch_arbeitnow_jobs
from app.services.job_sources.remotive import fetch_remotive_jobs
from app.services.job_sources.weworkremotely import fetch_weworkremotely_jobs

SOURCE_HANDLERS = {
    "remotive": fetch_remotive_jobs,
    "weworkremotely": fetch_weworkremotely_jobs,
    "arbeitnow": fetch_arbeitnow_jobs,
}


def free_sources_list() -> List[str]:
    return [s.strip().lower() for s in settings.free_sources.split(",") if s.strip()]


def fetch_jobs_from_sources(sources: List[str], limit_per_source: int = 60) -> List[Dict]:
    all_jobs: List[Dict] = []
    for source in sources:
        fetcher = SOURCE_HANDLERS.get(source)
        if not fetcher:
            continue
        try:
            all_jobs.extend(fetcher(limit=limit_per_source))
        except Exception:
            # Keep the pipeline alive if one source is temporarily failing.
            continue

    return _dedupe_by_url(all_jobs)


def _dedupe_by_url(jobs: List[Dict]) -> List[Dict]:
    seen = set()
    deduped = []
    for job in jobs:
        url = job.get("url", "")
        if not url or url in seen:
            continue
        deduped.append(job)
        seen.add(url)
    return deduped
