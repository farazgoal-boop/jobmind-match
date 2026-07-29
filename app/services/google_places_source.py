"""Google Places (New) integration — discovery only, scoped to the free
monthly tier by design.

Real pricing (checked live against developers.google.com/maps/billing-and-pricing
in 2026): Text Search (New) and Nearby Search (New) only exist at Pro
($32/1,000) and Enterprise ($35/1,000) tiers with a 5,000/month free
allowance each; Place Details (New) requesting `websiteUri` is a Pro-tier
field ($17/1,000) with its own separate 5,000/month free allowance. This
module tracks usage against both 5,000/month free allowances *before*
making a call, and refuses to make a call that would exceed either one — it
never silently starts incurring real cost. Usage tracking (get_usage,
would_exceed_free_tier, record_usage) must be verified working before this
module's actual API calls are trusted; that's the order this was built and
tested in.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from sqlmodel import Session

from app.models import AppSetting

logger = logging.getLogger("jobmind.leadhunter.places")

FREE_TIER_MONTHLY_LIMIT = 5000
_API_KEY_SETTING = "places_api_key"
_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
_REQUEST_TIMEOUT_S = 10


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _usage_setting_key(kind: str) -> str:
    return f"places_usage_{kind}_{_month_key()}"


def get_places_api_key(session: Session) -> str:
    row = session.get(AppSetting, _API_KEY_SETTING)
    return row.value if row else ""


def save_places_api_key(session: Session, key: str) -> None:
    cleaned = key.strip()
    session.merge(AppSetting(key=_API_KEY_SETTING, value=cleaned))
    session.commit()


def _get_usage_count(session: Session, kind: str) -> int:
    row = session.get(AppSetting, _usage_setting_key(kind))
    try:
        return int(row.value) if row else 0
    except ValueError:
        return 0


def get_usage(session: Session) -> dict[str, Any]:
    search_calls = _get_usage_count(session, "search")
    details_calls = _get_usage_count(session, "details")
    return {
        "month": _month_key(),
        "free_tier_limit": FREE_TIER_MONTHLY_LIMIT,
        "search_calls": search_calls,
        "search_remaining": max(0, FREE_TIER_MONTHLY_LIMIT - search_calls),
        "details_calls": details_calls,
        "details_remaining": max(0, FREE_TIER_MONTHLY_LIMIT - details_calls),
    }


def would_exceed_free_tier(session: Session, kind: str, additional: int = 1) -> bool:
    """kind is "search" or "details" — the two SKUs each have their own
    separate 5,000/month free allowance, so each is checked independently."""
    return _get_usage_count(session, kind) + additional > FREE_TIER_MONTHLY_LIMIT


def record_usage(session: Session, kind: str, count: int = 1) -> None:
    key = _usage_setting_key(kind)
    current = _get_usage_count(session, kind)
    session.merge(AppSetting(key=key, value=str(current + count)))
    session.commit()


def fetch_places_leads(session: Session, keywords: str, location: str) -> list[dict]:
    """Text Search (New) for businesses matching keywords+location, then
    Place Details (New) per result for its website URL — the two-stage
    design confirmed in the earlier assessment. Every result that has a
    real website URL comes back as a lead dict shaped exactly like every
    other source's (see lead_hunter_engine.py's PLATFORM_MAP dispatch), so
    it flows through the existing Pass 2 website crawl
    (website_crawler.py) unchanged: this module never reads email/whatsapp
    off a webpage itself, it only finds the business + its website.

    Refuses to run at all if: no API key is configured, no query can be
    built (no keywords and no location — Places search requires at least
    one), or making the call would exceed either SKU's free-tier
    allowance this month. Every one of these is a silent empty return, by
    design — see _gh_rate_limit_message()'s sibling reasoning in web.py:
    an empty list here must not be confused with 'found nothing', so
    callers needing to distinguish should check get_usage()/get_places_api_key()
    themselves before calling."""
    api_key = get_places_api_key(session)
    if not api_key:
        return []
    query = " ".join(part for part in (keywords.strip(), location.strip()) if part)
    if not query:
        return []

    if would_exceed_free_tier(session, "search"):
        logger.warning("places: search call skipped — would exceed %s/month free tier", FREE_TIER_MONTHLY_LIMIT)
        return []

    try:
        resp = requests.post(
            _TEXT_SEARCH_URL,
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
                "Content-Type": "application/json",
            },
            json={"textQuery": query, "pageSize": 20},
            timeout=_REQUEST_TIMEOUT_S,
        )
        record_usage(session, "search")
    except Exception:
        logger.exception("places: text search request failed")
        return []

    if resp.status_code != 200:
        logger.warning("places: text search returned %s: %s", resp.status_code, resp.text[:200])
        return []

    places = resp.json().get("places", []) or []
    leads: list[dict] = []
    for place in places:
        place_id = place.get("id", "")
        if not place_id:
            continue
        if would_exceed_free_tier(session, "details"):
            logger.warning("places: details call skipped — would exceed %s/month free tier", FREE_TIER_MONTHLY_LIMIT)
            break

        try:
            detail_resp = requests.get(
                _PLACE_DETAILS_URL.format(place_id=place_id),
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "displayName,websiteUri",
                },
                timeout=_REQUEST_TIMEOUT_S,
            )
            record_usage(session, "details")
        except Exception:
            logger.exception("places: place details request failed for %s", place_id)
            continue

        if detail_resp.status_code != 200:
            continue
        detail = detail_resp.json()
        website = detail.get("websiteUri", "")
        if not website:
            continue

        display_name = (place.get("displayName") or {}).get("text", "") or (detail.get("displayName") or {}).get("text", "")
        leads.append(
            {
                "name": display_name,
                "designation": "Business (Google Places)",
                "email": "",
                "whatsapp": "",
                "source": "google_places",
                "url": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                "website": website,
                "notes": place.get("formattedAddress", "")[:200],
                "location": location.strip(),
            }
        )
    return leads
