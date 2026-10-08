"""
Unit tests for search-result extraction against the Astro layout (issues #33, #36).

Loads a trimmed copy of a real kleinanzeigen.de results page into a local
Chromium page (no network) and runs the /inserate extraction on it.

Run with:
  pytest tests/test_extract_ads_astro.py -v
"""

import asyncio
import html
import json
from datetime import date, datetime
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from scrapers.inserate_ultra_optimized import (
    UltraOptimizedScraper,
    _page_has_old_listings,
    _parse_ad_previews,
)

FIXTURE = Path(__file__).parent / "fixtures" / "search_results_astro.html"


async def _extract(html: str) -> list:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - depends on local setup
            pytest.skip(f"Chromium not available: {exc}")
        try:
            page = await browser.new_page()
            await page.set_content(html)
            # Bypass __init__: extraction only needs the DOM helpers, not the
            # browser manager / uvloop setup.
            scraper = object.__new__(UltraOptimizedScraper)
            return await scraper.extract_ads_optimized(page)
        finally:
            await browser.close()


@pytest.fixture(scope="module")
def ads() -> dict:
    results = asyncio.run(_extract(FIXTURE.read_text(encoding="utf-8")))
    return {ad["adid"]: ad for ad in results}


def test_all_listings_extracted(ads):
    assert set(ads) == {"3501957949", "3525141008", "3523159642"}


def test_price_uses_current_price_not_strikethrough(ads):
    # Card shows "2.300 € VB" plus a struck-through old price "2.500 €"
    assert ads["3501957949"]["price"] == "2300"
    assert ads["3525141008"]["price"] == "120"
    assert ads["3523159642"]["price"] == "6999"


def test_description_is_filled(ads):
    assert ads["3501957949"]["description"].startswith("## Yamaha YZF-R6 RJ03")
    assert ads["3523159642"]["description"].startswith("Ich verkaufe meine Yamaha R6")
    # Badges below the price ("EZ 01/2006") must not leak into the description
    assert "EZ 01/" not in ads["3523159642"]["description"]


def test_published_at_today_format(ads):
    today = date.today()
    assert (
        ads["3525141008"]["published_at"]
        == datetime(today.year, today.month, today.day, 20, 6).isoformat()
    )


def test_published_at_date_format(ads):
    assert ads["3523159642"]["published_at"] == datetime(2026, 9, 25).isoformat()


def test_published_at_missing_is_none(ads):
    # Some cards (e.g. promoted listings) show no date at all, and this
    # fixture has no embedded preview data to fall back on
    assert ads["3501957949"]["published_at"] is None
    assert ads["3501957949"]["is_top_ad"] is False


def test_title_and_location_still_work(ads):
    ad = ads["3525141008"]
    assert ad["title"] == (
        "Bremspumpe Nissin Radial Pumpe Radial Bremse Hebel Yamaha R1 R6"
    )
    assert ad["location"] == "14979 Großbeeren"


def _astro(value):
    """Encode a value the way Astro serializes island props."""
    if isinstance(value, dict):
        return [0, {k: _astro(v) for k, v in value.items()}]
    if isinstance(value, list):
        return [1, [_astro(v) for v in value]]
    return [0, value]


# Mirrors the live page (2026-10-08): two TOP cards without a date, then the
# regular date-sorted listings. Dates for all cards live in the props of the
# ImpressionTracker island.
_RESULT_ADS = [
    {
        "sponsoredAdPresent": False,
        "organicAdPreview": {
            "id": 3436158201,
            "topAd": True,
            "sortingDate": "13.09.2026",
            "appliedFeatures": ["TOP_AD"],
        },
    },
    {
        "sponsoredAdPresent": False,
        "organicAdPreview": {
            "id": 3532985509,
            "topAd": True,
            "sortingDate": "06.10.2026",
            "appliedFeatures": ["TOP_AD"],
        },
    },
    {"sponsoredAdPresent": True, "sponsoredAd": {"positionName": "srps-result-list-3"}},
    {
        "sponsoredAdPresent": False,
        "organicAdPreview": {
            "id": 3535050266,
            "topAd": False,
            "sortingDate": "Heute, 20:45",
            "appliedFeatures": [],
        },
    },
]

_ISLAND_PROPS = json.dumps({"resultAds": _astro(_RESULT_ADS), "hasKeywords": _astro(True)})


def _card(adid: str, location: str, date_text: str = "") -> str:
    date_span = f"<div><svg></svg><span>{date_text}</span></div>" if date_text else ""
    return (
        f'<li><article data-adid="{adid}" data-href="/s-anzeige/x/{adid}-217-1">'
        f"<div><div><svg></svg><span>{location}</span></div>{date_span}</div>"
        f"<h3><a>Fahrrad {adid}</a></h3><p>Teaser</p></article></li>"
    )


TOP_AD_PAGE = (
    "<!doctype html><html><body><ul>"
    + _card("3436158201", "50259 Pulheim")
    + _card("3532985509", "77654 Offenburg")
    + _card("3535050266", "28201 Buntentor", "Heute, 20:45")
    + "</ul>"
    + f'<astro-island props="{html.escape(_ISLAND_PROPS, quote=True)}"></astro-island>'
    + "</body></html>"
)


@pytest.fixture(scope="module")
def top_ad_page_ads() -> dict:
    results = asyncio.run(_extract(TOP_AD_PAGE))
    return {ad["adid"]: ad for ad in results}


def test_top_ads_get_published_at_from_preview_data(top_ad_page_ads):
    # Issue #36: the first two (TOP) cards show no date on the card itself
    assert top_ad_page_ads["3436158201"]["published_at"] == datetime(2026, 9, 13).isoformat()
    assert top_ad_page_ads["3532985509"]["published_at"] == datetime(2026, 10, 6).isoformat()
    assert top_ad_page_ads["3436158201"]["is_top_ad"] is True
    assert top_ad_page_ads["3532985509"]["is_top_ad"] is True


def test_regular_ad_keeps_card_date(top_ad_page_ads):
    today = date.today()
    ad = top_ad_page_ads["3535050266"]
    assert ad["published_at"] == datetime(today.year, today.month, today.day, 20, 45).isoformat()
    assert ad["is_top_ad"] is False


def test_parse_ad_previews_skips_sponsored_and_invalid_props():
    previews = _parse_ad_previews([_ISLAND_PROPS, "not json", None])
    assert set(previews) == {"3436158201", "3532985509", "3535050266"}
    assert previews["3532985509"]["sortingDate"] == "06.10.2026"


def test_old_top_ad_does_not_stop_pagination():
    cutoff = datetime(2026, 10, 7)
    page = [
        {"published_at": "2026-09-13T00:00:00", "is_top_ad": True},
        {"published_at": "2026-10-08T20:45:00", "is_top_ad": False},
    ]
    assert _page_has_old_listings(page, cutoff) is False

    page.append({"published_at": "2026-10-06T23:59:00", "is_top_ad": False})
    assert _page_has_old_listings(page, cutoff) is True
