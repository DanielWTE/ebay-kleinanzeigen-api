"""Shared helpers for reading the Kleinanzeigen result-count breadcrumb.

Kleinanzeigen renders e.g. 'Autos 1 - 25 von 48 Gebrauchtwagen...' on search
pages. The total hit count is available on every page; the real page count is
only derivable on page 1, where the range always starts at 1.
"""

import math
import re

# Kleinanzeigen moved the summary from .breadcrump-summary to
# #srp-breadcrumb-summary; the selector list covers both markups.
TOTAL_RESULTS_SELECTOR = {
    "breadcrump_summary": "#srp-breadcrumb-summary, .breadcrump-summary"
}


def parse_breadcrumb(breadcrump_text: str) -> tuple[int | None, int | None]:
    """Parse the breadcrumb summary into (total_results, actual_page_count).

    Returns (None, None) if the text cannot be parsed at all. page_count is
    None when the range does not start at 1 (page size is ambiguous then).
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
