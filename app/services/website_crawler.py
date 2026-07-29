"""Pass 2 of lead hunting: crawl a candidate's own website for real contact
info.

The core fact driving this module: WhatsApp numbers almost never appear as
plain text on search results, GitHub bios, or article bodies (which is all
Pass 1's `_extract()` text-scan can see) — they appear as `wa.me/<number>`
or `api.whatsapp.com/send?phone=<number>` links embedded in a business's own
website (footer, contact page, chat widget). Reaching real WhatsApp volume
requires actually fetching that website's HTML and looking for those link
patterns, not scanning more text for phone-number-shaped substrings.

This module is deliberately conservative: it fetches at most two pages per
site (homepage + one discovered contact/footer page), respects robots.txt,
rate-limits itself per domain, and treats every failure as "found nothing"
rather than raising — a slow or hostile website must never take down a hunt
batch.
"""
from __future__ import annotations

import concurrent.futures
import logging
import re
import threading
import time
import urllib.robotparser
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("jobmind.leadhunter.crawler")

_USER_AGENT = "Mozilla/5.0 (compatible; JobMindMatchBot/1.0; +https://github.com/farazgoal-boop/jobmind-match)"
_PAGE_TIMEOUT_S = 6
_MIN_SECONDS_BETWEEN_REQUESTS_PER_DOMAIN = 2.0
_MAX_WORKERS = 5

_WA_LINK_RE = re.compile(
    r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)\+?(\d[\d\-\s]{6,17}\d)",
    re.IGNORECASE,
)
_MAILTO_RE = re.compile(r"mailto:([^\"'\s?&>]+)", re.IGNORECASE)
_CONTACT_LINK_WORDS = ("contact", "get in touch", "reach us", "about")
_CONTACT_PATH_HINTS = ("contact", "about", "get-in-touch", "reach-us")

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_robots_lock = threading.Lock()
_domain_last_hit: dict[str, float] = {}
_domain_lock = threading.Lock()


def normalize_whatsapp_e164(raw: str) -> str:
    """'+1 (555) 123-4567' / '0015551234567' / '15551234567' -> '+15551234567'.
    Returns '' if the digit count doesn't look like a real phone number."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if not (8 <= len(digits) <= 15):
        return ""
    return f"+{digits}"


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _robots_allows(url: str) -> bool:
    domain = _domain_of(url)
    if not domain:
        return False
    with _robots_lock:
        parser = _robots_cache.get(domain)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(f"{urlparse(url).scheme}://{domain}/robots.txt")
            try:
                parser.read()
            except Exception:
                # No readable robots.txt is treated as "allowed" (matches
                # standard crawler behavior — absence of a policy is not a
                # disallow), not a reason to skip an otherwise-public site.
                parser = None
            _robots_cache[domain] = parser
    if parser is None:
        return True
    try:
        return parser.can_fetch(_USER_AGENT, url)
    except Exception:
        return True


def _respect_domain_rate_limit(domain: str) -> None:
    with _domain_lock:
        last = _domain_last_hit.get(domain, 0.0)
        wait = _MIN_SECONDS_BETWEEN_REQUESTS_PER_DOMAIN - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        _domain_last_hit[domain] = time.monotonic()


def _fetch_page(url: str) -> str | None:
    if not _robots_allows(url):
        return None
    _respect_domain_rate_limit(_domain_of(url))
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_PAGE_TIMEOUT_S)
        if resp.status_code != 200 or not resp.text:
            return None
        return resp.text
    except Exception:
        return None


def _extract_from_html(html: str) -> dict[str, str]:
    whatsapp = ""
    email = ""
    wa_match = _WA_LINK_RE.search(html)
    if wa_match:
        whatsapp = normalize_whatsapp_e164(wa_match.group(1))
    mail_match = _MAILTO_RE.search(html)
    if mail_match:
        candidate = mail_match.group(1).strip()
        # mailto: hrefs are sometimes ?subject=... suffixed even without a
        # '?' delimiter reaching the regex boundary (e.g. ';subject=' MUAs).
        candidate = candidate.split(";")[0].strip()
        if "@" in candidate and "." in candidate.split("@")[-1]:
            email = candidate
    return {"whatsapp": whatsapp, "email": email}


def _find_contact_page(base_url: str, html: str) -> str | None:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        text = (a.get_text() or "").strip().lower()
        href_lower = href.lower()
        if any(word in text for word in _CONTACT_LINK_WORDS) or any(
            hint in href_lower for hint in _CONTACT_PATH_HINTS
        ):
            absolute = urljoin(base_url, href)
            if _domain_of(absolute) == _domain_of(base_url):
                return absolute
    return None


def crawl_website_for_contacts(website_url: str) -> dict[str, Any]:
    """Fetch a candidate's homepage (+ one contact/footer page if found) and
    return any WhatsApp/email discovered as real `wa.me`/`mailto:` links.
    Never raises — network failures, robots.txt disallows, and parse errors
    all resolve to an empty (not-found) result."""
    result: dict[str, Any] = {
        "whatsapp": "", "whatsapp_method": "", "email": "", "email_method": "",
        "pages_crawled": 0,
    }
    url = website_url.strip()
    if not url:
        return result
    if not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"
    if not _domain_of(url):
        return result

    homepage_html = _fetch_page(url)
    if homepage_html is None:
        return result
    result["pages_crawled"] += 1
    found = _extract_from_html(homepage_html)
    if found["whatsapp"]:
        result["whatsapp"], result["whatsapp_method"] = found["whatsapp"], "wa_me_link"
    if found["email"]:
        result["email"], result["email_method"] = found["email"], "mailto_link"

    if not (result["whatsapp"] and result["email"]):
        contact_url = _find_contact_page(url, homepage_html)
        if contact_url and contact_url != url:
            contact_html = _fetch_page(contact_url)
            if contact_html is not None:
                result["pages_crawled"] += 1
                found = _extract_from_html(contact_html)
                if not result["whatsapp"] and found["whatsapp"]:
                    result["whatsapp"], result["whatsapp_method"] = found["whatsapp"], "wa_me_link"
                if not result["email"] and found["email"]:
                    result["email"], result["email_method"] = found["email"], "mailto_link"

    return result


def crawl_websites_bounded(urls: list[str], max_workers: int = _MAX_WORKERS) -> dict[str, dict[str, Any]]:
    """Crawl multiple candidate websites concurrently, bounded by a worker
    pool (never one request per site all at once — that's what the per-domain
    rate limit and robots.txt are for individually, this just caps overall
    fan-out). Returns {url: crawl_website_for_contacts(url)}; a per-site
    exception resolves to that site's empty default rather than aborting the
    others."""
    results: dict[str, dict[str, Any]] = {}
    if not urls:
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="wacrawl") as pool:
        future_to_url = {pool.submit(crawl_website_for_contacts, u): u for u in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception:
                logger.exception("website crawl: unhandled failure for %s", url)
                results[url] = {
                    "whatsapp": "", "whatsapp_method": "", "email": "", "email_method": "",
                    "pages_crawled": 0,
                }
    return results
