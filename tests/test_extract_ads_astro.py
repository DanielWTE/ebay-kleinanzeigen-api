"""
Unit tests for search-result extraction against the Astro layout (issue #33).

Loads a trimmed copy of a real kleinanzeigen.de results page into a local
Chromium page (no network) and runs the /inserate extraction on it.

Run with:
  pytest tests/test_extract_ads_astro.py -v
"""

import asyncio
from datetime import date, datetime
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from scrapers.inserate_ultra_optimized import UltraOptimizedScraper

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
    # Some cards (e.g. promoted listings) show no date at all
    assert ads["3501957949"]["published_at"] is None


def test_title_and_location_still_work(ads):
    ad = ads["3525141008"]
    assert ad["title"] == (
        "Bremspumpe Nissin Radial Pumpe Radial Bremse Hebel Yamaha R1 R6"
    )
    assert ad["location"] == "14979 Großbeeren"
