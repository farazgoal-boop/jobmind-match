"""Lead hunter orchestration: 200+ platforms + permanent dedup registry."""
from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Any

from sqlmodel import Session

from app.services.lead_hunter_registry import (
    filter_new_leads,
    load_dnc_keys,
    load_known_keys,
    register_leads,
    _norm_email,
    _norm_whatsapp,
)
from app.services.lead_platforms import PLATFORM_MAP, PLATFORMS, get_hunt_plan, platform_summary

logger = logging.getLogger("jobmind.leadhunter")

# A single hung/rate-limited source (e.g. a slow chain of sequential HTTP
# calls) must never block the whole request — cap every source fetch to a
# hard wall-clock budget and surface a real error instead of hanging.
_SOURCE_TIMEOUT_SECONDS = 25
# Sized to match the dashboard's concurrent-platform hunt lanes (see
# dashboard.html's LHP_CONCURRENCY) so genuine parallel fetches actually run
# in parallel here instead of queuing behind a smaller pool.
_SCRAPE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=6, thread_name_prefix="leadhunt"
)

# Pass 2 (website crawl for wa.me/mailto links) is best-effort enrichment on
# top of Pass 1's fetch — bounded independently so a batch of slow/hostile
# candidate sites can never make a single /api/scrape/leads call hang
# indefinitely. Unfinished crawls at the deadline are simply dropped from
# this batch's results, not retried.
_MAX_WEBSITES_PER_BATCH = 8
_WEBSITE_CRAWL_BUDGET_SECONDS = 15


def list_platforms() -> list[dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "type": p["type"],
            "chip": p["chip"],
            "batches": p["batches"],
        }
        for p in PLATFORMS
    ]


def build_hunt_plan(enabled_chips: list[str]) -> list[dict[str, Any]]:
    return get_hunt_plan(enabled_chips)


def _uses_native_location_qualifier(source: str) -> bool:
    """True for platform types where GitHub's own `location:` search qualifier applies —
    real profile metadata, not a text scrape, so no soft-filter is needed afterward."""
    platform = PLATFORM_MAP.get(source)
    ptype = platform["type"] if platform else source
    return ptype == "github"


def _matches_location(lead: dict, locations: list[str]) -> bool:
    """True if the lead's text mentions any of the candidate place names — used to
    broaden a single pin/city into a whole resolved radius of real places."""
    needles = [loc.strip().lower() for loc in locations if loc.strip()]
    if not needles:
        return True
    haystack = " ".join(
        str(lead.get(field, ""))
        for field in ("name", "designation", "notes", "location")
    ).lower()
    return any(needle in haystack for needle in needles)


def fetch_for_source(source: str, offset: int, keywords: str = "", location: str = "") -> list[dict]:
    """Dispatch a platform id (or legacy source key) to the scraper layer."""
    from app.routes import web as scrapers

    platform = PLATFORM_MAP.get(source)
    kw = keywords.strip()
    loc = location.strip()

    if platform:
        ptype = platform["type"]
        if ptype == "github":
            query = scrapers.GH_SEARCH_QUERIES[platform.get("query_index", 0) % len(scrapers.GH_SEARCH_QUERIES)]
            if kw:
                query = f"{query} {kw}"
            if loc:
                query = f'{query} location:"{loc}"'
            page = offset + 1
            return scrapers._fetch_github_profiles(query, page=page)
        if ptype == "github_readme":
            query = kw or scrapers.GH_SEARCH_QUERIES[offset % len(scrapers.GH_SEARCH_QUERIES)]
            return scrapers._fetch_github_readme(query, page=(offset // 5) + 1)
        if ptype == "github_issues":
            return scrapers._fetch_github_jobs_rss()
        if ptype == "devto":
            tag = platform.get("tag") or scrapers.DEVTO_TAGS[offset % len(scrapers.DEVTO_TAGS)]
            if kw:
                tag = kw
            page = (offset // max(len(scrapers.DEVTO_TAGS), 1)) + 1
            return scrapers._fetch_devto_articles(tag, page=page)
        if ptype == "hackernews":
            return scrapers._fetch_hackernews()
        if ptype == "indiehackers":
            return scrapers._fetch_indiehackers()
        if ptype == "remotive":
            return scrapers._fetch_remotive_rss()
        if ptype == "weworkremotely":
            return scrapers._fetch_weworkremotely_rss()
        if ptype == "reddit":
            sub = platform.get("subreddit") or platform.get("sub") or "forhire"
            return scrapers._fetch_reddit_rss(sub)
        if ptype == "rss":
            return _fetch_rss_feed(platform.get("feed_url") or platform.get("url", ""), platform["name"])
        if ptype == "site":
            return _fetch_site_contacts(platform.get("site", ""), kw, offset)
        if ptype == "arbeitnow":
            return _fetch_arbeitnow_contacts()

    # Legacy source keys (backward compatible)
    if source == "github":
        kw_idx = offset % len(scrapers.GH_SEARCH_QUERIES)
        kw_to_use = scrapers.GH_SEARCH_QUERIES[kw_idx] + (f" {kw}" if kw else "")
        if loc:
            kw_to_use = f'{kw_to_use} location:"{loc}"'
        return scrapers._fetch_github_profiles(kw_to_use, page=(offset // len(scrapers.GH_SEARCH_QUERIES)) + 1)
    if source == "github_readme":
        query = f"freelance developer email {kw}" if kw else scrapers.GH_SEARCH_QUERIES[offset % len(scrapers.GH_SEARCH_QUERIES)]
        return scrapers._fetch_github_readme(query, page=(offset // 5) + 1)
    if source == "github_issues":
        return scrapers._fetch_github_jobs_rss()
    if source == "devto":
        tag = kw or scrapers.DEVTO_TAGS[offset % len(scrapers.DEVTO_TAGS)]
        return scrapers._fetch_devto_articles(tag, page=(offset // len(scrapers.DEVTO_TAGS)) + 1)
    if source == "hackernews":
        return scrapers._fetch_hackernews()
    if source == "indiehackers":
        return scrapers._fetch_indiehackers()
    if source == "remotive":
        return scrapers._fetch_remotive_rss()
    if source == "weworkremotely":
        return scrapers._fetch_weworkremotely_rss()
    if source == "reddit_rss":
        subs = ["forhire", "freelance", "slavelabour", "hiring", "WorkOnline"]
        return scrapers._fetch_reddit_rss(subs[offset % len(subs)])

    return []


def run_scrape_batch(
    session: Session,
    source: str,
    offset: int,
    keywords: str = "",
    location: str = "",
    locations: list[str] | None = None,
    hunt_session_id: int | None = None,
) -> dict[str, Any]:
    t0 = time.monotonic()
    loc = location.strip()
    # `locations` is the full radius-resolved place list (Phase 2b); `loc` (the
    # originally-picked pin/city) is always included so single-place hunts still work.
    candidate_places = [p for p in [loc, *(locations or [])] if p.strip()]
    platform = PLATFORM_MAP.get(source)
    known_emails, known_whatsapp = load_known_keys(session)

    def _log(reason: str, **counts: int) -> None:
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        parts = " ".join(f"{k}={v}" for k, v in counts.items())
        logger.info(
            "lead hunt: source=%s offset=%s elapsed_ms=%s reason=%s %s",
            source, offset, elapsed_ms, reason, parts,
        )

    def _timeout_result(error: str) -> dict[str, Any]:
        return {
            "leads": [],
            "count": 0,
            "source": source,
            "platform": platform["name"] if platform else source,
            "offset": offset,
            "skipped_known": 0,
            "registry_total": len(known_emails) + len(known_whatsapp),
            "error": error,
        }

    future = _SCRAPE_EXECUTOR.submit(fetch_for_source, source, offset, keywords, loc)
    try:
        raw_leads = future.result(timeout=_SOURCE_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        _log("timeout", attempted=0, fresh=0)
        logger.warning(
            "lead hunt: source=%s offset=%s timed out after %ss",
            source, offset, _SOURCE_TIMEOUT_SECONDS,
        )
        return _timeout_result(f"Timed out after {_SOURCE_TIMEOUT_SECONDS}s — source skipped.")
    except Exception as exc:
        _log("error", attempted=0, fresh=0)
        logger.exception("lead hunt: source=%s offset=%s raised", source, offset)
        return _timeout_result(str(exc))

    fetched = len(raw_leads)

    if candidate_places:
        native = _uses_native_location_qualifier(source)
        kept = []
        for lead in raw_leads:
            if native or _matches_location(lead, candidate_places):
                if not lead.get("location"):
                    lead["location"] = loc or candidate_places[0]
                kept.append(lead)
        raw_leads = kept
    location_filtered = fetched - len(raw_leads)

    # Pass 2: crawl each candidate's own website (if Pass 1 found one — e.g.
    # GitHub's profile "blog" field) for wa.me/mailto links. This is the
    # actual mechanism that finds WhatsApp numbers at any real volume — see
    # website_crawler.py's module docstring for why text-scanning alone
    # (Pass 1) essentially never does. Skips leads that already have both
    # contact fields; caps how many sites one batch will crawl so a source
    # with many candidates can't blow the batch's wall-clock budget.
    website_pages_crawled = 0
    website_contacts_found = 0
    crawl_candidates = [
        lead for lead in raw_leads
        if lead.get("website") and not (lead.get("whatsapp") and lead.get("email"))
    ][:_MAX_WEBSITES_PER_BATCH]
    if crawl_candidates:
        from app.services.website_crawler import crawl_websites_bounded

        crawl_results: dict[str, dict] = {}
        crawl_urls = [lead["website"] for lead in crawl_candidates]
        crawl_future = _SCRAPE_EXECUTOR.submit(crawl_websites_bounded, crawl_urls)
        try:
            crawl_results = crawl_future.result(timeout=_WEBSITE_CRAWL_BUDGET_SECONDS)
        except concurrent.futures.TimeoutError:
            logger.warning(
                "lead hunt: source=%s offset=%s website crawl exceeded %ss budget, using partial results",
                source, offset, _WEBSITE_CRAWL_BUDGET_SECONDS,
            )
        except Exception:
            logger.exception("lead hunt: source=%s offset=%s website crawl failed", source, offset)

        for lead in crawl_candidates:
            found = crawl_results.get(lead["website"])
            if not found:
                continue
            website_pages_crawled += found.get("pages_crawled", 0)
            gained = False
            if not lead.get("whatsapp") and found.get("whatsapp"):
                lead["whatsapp"] = found["whatsapp"]
                lead["whatsapp_method"] = found["whatsapp_method"]
                gained = True
            if not lead.get("email") and found.get("email"):
                lead["email"] = found["email"]
                lead["email_method"] = found["email_method"]
                gained = True
            if gained:
                website_contacts_found += 1

    dnc_filtered = 0
    if raw_leads:
        dnc_emails, dnc_whatsapp = load_dnc_keys(session)
        if dnc_emails or dnc_whatsapp:
            before_dnc = len(raw_leads)
            raw_leads = [
                lead
                for lead in raw_leads
                if _norm_email(lead.get("email", "")) not in dnc_emails
                and _norm_whatsapp(lead.get("whatsapp", "")) not in dnc_whatsapp
            ]
            dnc_filtered = before_dnc - len(raw_leads)

    fresh, skipped = filter_new_leads(raw_leads, known_emails, known_whatsapp)
    if fresh:
        register_leads(session, fresh, hunt_session_id=hunt_session_id)

    _log(
        "ok",
        attempted=fetched,
        location_filtered=location_filtered,
        dnc_filtered=dnc_filtered,
        duplicate=skipped,
        fresh=len(fresh),
        websites_crawled=len(crawl_candidates),
        website_pages=website_pages_crawled,
        website_contacts_found=website_contacts_found,
    )
    return {
        "leads": fresh,
        "count": len(fresh),
        "source": source,
        "platform": platform["name"] if platform else source,
        "offset": offset,
        "skipped_known": skipped,
        "registry_total": len(known_emails) + len(known_whatsapp),
        "error": "",
    }


def _fetch_rss_feed(feed_url: str, label: str) -> list[dict]:
    from app.routes.web import _extract, _desig, _hdr
    import re
    import xml.etree.ElementTree as ET
    import requests as _req

    leads: list[dict] = []
    if not feed_url:
        return leads
    try:
        response = _req.get(feed_url, headers=_hdr(), timeout=15)
        if response.status_code != 200:
            return leads
        root = ET.fromstring(response.content)
        for item in root.findall(".//item")[:25]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            desc = item.findtext("description") or ""
            body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or desc
            text = re.sub(r"<[^>]+>", " ", f"{title} {body}")
            emails, wa = _extract(text)
            if emails or wa:
                leads.append(
                    {
                        "name": title[:60] or label,
                        "designation": _desig(title),
                        "email": emails[0] if emails else "",
                        "whatsapp": wa[0] if wa else "",
                        "source": label.lower().replace(" ", "_")[:40],
                        "url": link,
                        "notes": title[:100],
                    }
                )
    except Exception:
        return leads
    return leads


def _fetch_site_contacts(site: str, keywords: str, offset: int) -> list[dict]:
    """Lightweight public-page contact extraction for marketplace domains."""
    from app.routes.web import _extract, _desig, _hdr
    import requests as _req
    from bs4 import BeautifulSoup

    if not site:
        return []
    paths = ["/", "/contact", "/about", "/hire", "/freelancers"]
    path = paths[offset % len(paths)]
    query = keywords or "freelance contact email whatsapp"
    urls = [
        f"https://{site}{path}",
        f"https://www.{site}{path}",
    ]
    leads: list[dict] = []
    for url in urls:
        try:
            response = _req.get(url, headers=_hdr(), timeout=12)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            if query:
                text = f"{text} {query}"
            emails, wa = _extract(text)
            for email in emails[:3]:
                leads.append(
                    {
                        "name": site.split(".")[0].title(),
                        "designation": "Marketplace / Seller",
                        "email": email,
                        "whatsapp": wa[0] if wa else "",
                        "source": site,
                        "url": url,
                        "notes": f"Found on {site}",
                    }
                )
            if leads:
                break
        except Exception:
            continue
    return leads


def _fetch_arbeitnow_contacts() -> list[dict]:
    from app.routes.web import _extract, _desig
    from app.services.job_sources.arbeitnow import fetch_arbeitnow_jobs

    leads: list[dict] = []
    try:
        for job in fetch_arbeitnow_jobs(limit=40):
            text = f"{job.get('title','')} {job.get('company','')} {job.get('description','')}"
            emails, wa = _extract(text)
            if emails or wa:
                leads.append(
                    {
                        "name": job.get("company") or job.get("title", "")[:50],
                        "designation": _desig(job.get("title", "")),
                        "email": emails[0] if emails else "",
                        "whatsapp": wa[0] if wa else "",
                        "source": "arbeitnow",
                        "url": job.get("url", ""),
                        "notes": job.get("title", "")[:100],
                    }
                )
    except Exception:
        return leads
    return leads


def summary() -> dict[str, Any]:
    return platform_summary()
