"""
URL-passthrough scraper: takes a full Kleinanzeigen URL and injects page numbers.
Reuses UltraOptimizedScraper for fetching/extraction; only the URL-building differs.
"""

import asyncio
import gc
import logging
import math
import re
from datetime import datetime
from typing import Any

from scrapers.inserate_ultra_optimized import (
    _filter_by_min_publish_date,
    _page_has_old_listings,
    create_ultra_optimized_scraper,
)
from utils.browser import OptimizedPlaywrightManager
from utils.performance import PerformanceTracker

_TOTAL_RESULTS_SELECTOR = {"breadcrump_summary": ".breadcrump-summary"}


def inject_page(url: str, page_num: int) -> str:
    """
    Strip any existing seite/s-seite segment and inject the requested page number.

    Category URLs: seite:N is inserted immediately before the filter segment
    (the segment matching k?\\d*c\\d+), preserving any extra path components
    (e.g. anzeige:angebote, preis::N) that appear before it:
      /s-autos/anzeige:angebote/preis::15000/seite:2/c216+...
    Generic search URLs (no filter segment): s-seite:N appended before the query string.
    """
    from urllib.parse import unquote, urlparse, urlunparse

    parsed = urlparse(url)
    path = unquote(parsed.path)

    # Strip any existing page segment
    segments = [
        s
        for s in path.strip("/").split("/")
        if s and not re.match(r"^s-seite:\d+$", s) and not re.match(r"^seite:\d+$", s)
    ]

    if page_num > 1:
        filter_idx = next(
            (i for i, s in enumerate(segments) if re.match(r"^k?\d*c\d+", s)),
            None,
        )
        if filter_idx is not None:
            # Insert seite:N directly before the filter segment
            segments.insert(filter_idx, f"seite:{page_num}")
        else:
            # Generic search: append s-seite:N before query string
            segments.append(f"s-seite:{page_num}")

    new_path = "/" + "/".join(segments)
    return urlunparse(parsed._replace(path=new_path))


def _parse_breadcrumb(breadcrump_text: str) -> tuple[int | None, int | None]:
    """Parse the breadcrumb summary into (total_results, actual_page_count).

    Kleinanzeigen renders e.g. 'Autos 1 - 25 von 48 Gebrauchtwagen...'
    Page size is only unambiguous on page 1 (range always starts at 1), so
    page_count is only computed then; otherwise returns None for page_count.
    Returns (None, None) if the text cannot be parsed at all.
    """
    match = re.search(r"(\d[\d.]*)\s*-\s*(\d[\d.]*)\s+von\s+([\d.]+)", breadcrump_text)
    if not match:
        return None, None
    page_start = int(match.group(1).replace(".", ""))
    page_end = int(match.group(2).replace(".", ""))
    total = int(match.group(3).replace(".", ""))
    if page_start != 1:
        # Can't derive page size from a partial last-page range
        return total, None
    page_size = page_end  # page_end - 1 + 1
    if page_size <= 0:
        return total, None
    return total, math.ceil(total / page_size)


async def scrape_by_url(
    browser_manager: OptimizedPlaywrightManager,
    base_url: str,
    max_pages: int = 1,
    min_publish_date: datetime | None = None,
) -> dict[str, Any]:
    """Scrape up to max_pages pages starting from base_url.

    If min_publish_date is set, stops fetching once a page contains listings
    older than that date and trims those listings from the final results.
    """
    scraper = await create_ultra_optimized_scraper(browser_manager)
    tracker = PerformanceTracker()
    tracker.start_request()

    try:
        batch_size = min(8, max_pages)
        all_results = []
        all_metrics = []
        total_results: int | None = None
        actual_max_pages: int | None = None
        _log = logging.getLogger("scrape_by_url")

        # Fetch pages sequentially — Kleinanzeigen blocks concurrent requests
        # from the same IP even with staggered starts.
        # A short delay between pages further reduces bot-detection risk.
        for page_num in range(1, max_pages + 1):
            # After page 1 we know the real page count — stop before wasting requests.
            if actual_max_pages is not None and page_num > actual_max_pages:
                _log.info(
                    f"[OVERVIEW] stopping after page {page_num - 1} "
                    f"(breadcrumb says {actual_max_pages} page(s) total, "
                    f"{total_results} results)"
                )
                break

            if page_num > 1:
                await asyncio.sleep(2)
            result = await scraper.ultra_optimized_fetch_page(
                inject_page(base_url, page_num),
                page_num,
                extra_selectors=_TOTAL_RESULTS_SELECTOR if page_num == 1 else None,
            )
            if not isinstance(result, Exception):
                page_results, page_metrics, extras = result

                if total_results is None and "breadcrump_summary" in extras:
                    total_results, actual_max_pages = _parse_breadcrumb(
                        extras["breadcrump_summary"]
                    )
                    effective = (
                        min(max_pages, actual_max_pages)
                        if actual_max_pages is not None
                        else max_pages
                    )
                    _log.info(
                        f"[OVERVIEW] breadcrumb: {total_results} results → "
                        f"{actual_max_pages} page(s) available, "
                        f"fetching up to {effective}"
                    )

                if not page_results:
                    _log.info(
                        f"[OVERVIEW] page {page_num} returned no results — stopping early"
                    )
                    all_metrics.append(page_metrics)
                    tracker.add_page_metric(page_metrics)
                    break

                stop = min_publish_date and _page_has_old_listings(
                    page_results, min_publish_date
                )
                if min_publish_date:
                    page_results = _filter_by_min_publish_date(
                        page_results, min_publish_date
                    )

                all_results.extend(page_results)
                all_metrics.append(page_metrics)
                tracker.add_page_metric(page_metrics)

                if stop:
                    break
            gc.collect()

        pages_attempted = len(all_metrics)
        tracker.set_concurrent_level(batch_size)
        browser_metrics = browser_manager.get_performance_metrics()
        tracker.set_browser_contexts_used(
            browser_metrics["contexts_in_use"] + browser_metrics["contexts_in_pool"]
        )
        request_metrics = tracker.get_request_metrics()
        request_metrics_dict = request_metrics.to_dict()

        successful_pages = sum(1 for m in all_metrics if m.success)
        success_rate = (
            (successful_pages / pages_attempted) * 100 if pages_attempted > 0 else 0
        )

        response = {
            "success": True,
            "results": all_results,
            "unique_results": len(all_results),
            "time_taken": round(request_metrics.total_time, 3),
            "performance_metrics": {
                "pages_requested": pages_attempted,
                "pages_successful": successful_pages,
                "success_rate": round(success_rate, 2),
                "average_page_time": round(
                    request_metrics_dict.get("average_page_time", 0), 3
                ),
            },
            "browser_metrics": browser_metrics,
        }

        if total_results is not None:
            response["total_results"] = total_results

        return response
    finally:
        await scraper.cleanup()
