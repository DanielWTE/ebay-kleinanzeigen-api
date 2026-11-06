"""
Parse a Kleinanzeigen URL and extract all known parameters as JSON.

Usage:
  python tests/parse_url.py <url>

Examples:
  python tests/parse_url.py "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/c220+wohnwagen_mobile.art_s:wohnwagen+wohnwagen_mobile.ez_i:2008%2C"
  python tests/parse_url.py "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/preis:1000:15000/klima/k0c220+wohnwagen_mobile.art_s:wohnwagen+wohnwagen_mobile.ez_i:2008%2C+wohnwagen_mobile.marke_s:(fendt%2Cknaus)"
"""

import json
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse


def parse_kleinanzeigen_url(url: str) -> dict:
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")
    qs = parse_qs(parsed.query)

    result = {}

    # ── Query-string params ───────────────────────────────────────────────
    if "keywords" in qs:
        result["query"] = qs["keywords"][0]
    if "locationStr" in qs:
        result["location"] = qs["locationStr"][0]
    if "radius" in qs:
        result["radius"] = int(qs["radius"][0])

    # ── Path segments ─────────────────────────────────────────────────────
    segments = path.split("/")

    filter_segment = None

    for i, seg in enumerate(segments):
        # Page — seite:2
        if seg.startswith("seite:") or re.match(r"^s-seite:\d+$", seg):
            result["page"] = int(seg.split(":")[1])

        # Category slug — s-wohnwagen-mobile  (first segment starting with s-)
        elif seg.startswith("s-") and "category_slug" not in result:
            result["category_slug"] = seg

        # Price range — preis:1000:15000
        elif seg.startswith("preis:"):
            parts = seg.split(":")
            if parts[1]:
                result["min_price"] = int(parts[1])
            if parts[2]:
                result["max_price"] = int(parts[2])

        # Filter segment — c220+... or k0c220+...
        elif re.match(r"^k?\d*c\d+", seg):
            filter_segment = seg

        # Subcategory — second meaningful segment (not a filter/price/page)
        elif i == 1:
            result["subcategory"] = seg

        # Path keyword — sits between subcategory and filter segment
        elif filter_segment is None and i > 1:
            result["path_keyword"] = seg

    # ── Filter segment ────────────────────────────────────────────────────
    if filter_segment:
        # Strip k0 prefix (present when a path keyword exists)
        fs = filter_segment.removeprefix("k0")

        for attr in fs.split("+"):
            # Category ID — c220
            if re.match(r"^c\d+$", attr):
                result["category_id"] = int(attr[1:])
                continue

            if ":" not in attr:
                continue

            key, value = attr.split(":", 1)

            # Year — *.ez_i:2008,   (trailing comma = open-ended range)
            if key.endswith(".ez_i"):
                year_str = value.rstrip(",")
                if year_str:
                    result["year_from"] = int(year_str)
                if value.endswith(","):
                    result["year_to"] = None  # open-ended

            # Article type — *.art_s:wohnwagen
            elif key.endswith(".art_s"):
                result["art"] = value

            # Brands — *.marke_s:(fendt,knaus)  or  *.marke_s:fendt
            elif key.endswith(".marke_s"):
                if value.startswith("(") and value.endswith(")"):
                    result["brands"] = value[1:-1].split(",")
                else:
                    result["brands"] = [value]

            # Any other attribute we don't know yet
            else:
                result.setdefault("unknown_attrs", {})[key] = value

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/parse_url.py <kleinanzeigen-url>")
        sys.exit(1)

    url = sys.argv[1]
    result = parse_kleinanzeigen_url(url)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
