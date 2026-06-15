"""Lead hunter orchestration: 200+ platforms + permanent dedup registry."""
from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.services.lead_hunter_registry import filter_new_leads, load_known_keys, register_leads
from app.services.lead_platforms import PLATFORM_MAP, PLATFORMS, get_hunt_plan, platform_summary


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


def fetch_for_source(source: str, offset: int, keywords: str = "") -> list[dict]:
    """Dispatch a platform id (or legacy source key) to the scraper layer."""
    from app.routes import web as scrapers

    platform = PLATFORM_MAP.get(source)
    kw = keywords.strip()

    if platform:
        ptype = platform["type"]
        if ptype == "github":
            query = scrapers.GH_SEARCH_QUERIES[platform.get("query_index", 0) % len(scrapers.GH_SEARCH_QUERIES)]
            if kw:
                query = f"{query} {kw}"
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
) -> dict[str, Any]:
    raw_leads = fetch_for_source(source, offset, keywords)
    known_emails, known_whatsapp = load_known_keys(session)
    fresh, skipped = filter_new_leads(raw_leads, known_emails, known_whatsapp)
    if fresh:
        register_leads(session, fresh)
    platform = PLATFORM_MAP.get(source)
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
