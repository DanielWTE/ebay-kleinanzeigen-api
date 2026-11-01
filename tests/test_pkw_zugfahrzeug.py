"""
Fetch PKW Zugfahrzeug listings via POST /inserate-by-url.

Usage:
  python tests/test_pkw_zugfahrzeug.py                                          # 1 page per URL
  python tests/test_pkw_zugfahrzeug.py --max-pages 3
  python tests/test_pkw_zugfahrzeug.py --max-pages 10 --min-publish-date 2026-05-04T08:00:00
"""

import asyncio
import json
import sys

import aiohttp

BASE_URL = "http://localhost:8000"

SEARCHES = [
    {
        "label": "Zugfahrzeug Luxus & Premium Fendt, Tabbert, Eriba, Klima, max 15.000 €, ab 2008",
        "url": (
            "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/preis::15000/klima/"
            "k0c220+wohnwagen_mobile.art_s:wohnwagen+wohnwagen_mobile.ez_i:2008%2C"
            "+wohnwagen_mobile.marke_s:(fendt%2Chymer-eriba%2Ctabbert)"
        ),
    },
    {
        "label": "Wohnwagen gehoben Adria, Dethleffs, Knaus, LMC,  Klima, max 15.000 €, ab 2008",
        "url": (
            "https://www.kleinanzeigen.de/s-wohnwagen-mobile/wohnwagen/preis::15000/klima/"
            "k0c220+wohnwagen_mobile.art_s:wohnwagen+wohnwagen_mobile.ez_i:2008%2C"
            "+wohnwagen_mobile.marke_s:(adria%2Cdethleffs%2Cknaus%2Clmc)"
        ),
    },
]


async def run_search(
    session: aiohttp.ClientSession,
    search: dict,
    max_pages: int,
    min_publish_date: str | None,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"Search: {search['label']}")
    print(f"URL:    {search['url']}")
    if min_publish_date:
        print(f"Since:  {min_publish_date}")
    print(f"{'=' * 60}")

    payload: dict = {"url": search["url"], "max_pages": max_pages}
    if min_publish_date:
        payload["min_publish_date"] = min_publish_date

    try:
        async with session.post(
            f"{BASE_URL}/inserate-by-url",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=600),
        ) as resp:
            print(f"HTTP status: {resp.status}")
            raw = await resp.text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print(f"Non-JSON response:\n{raw[:500]}")
                return

            if not data.get("success"):
                print(f"API error: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return

            listings = data.get("results", [])
            metrics = data.get("performance_metrics", {})

            print(f"Total results  : {data.get('total_results', 'N/A')}")
            print(f"Fetched        : {len(listings)}")
            print(f"Pages fetched  : {metrics.get('pages_requested', '?')}")
            print(f"Pages OK       : {metrics.get('pages_successful', '?')}")
            print(f"Success rate   : {metrics.get('success_rate', 0):.1f}%")
            print(f"Time taken     : {data.get('time_taken', 0):.1f}s")

            if not listings:
                print("\nNo listings returned.")
                return

            print(f"\n{'─' * 60}")
            for i, item in enumerate(listings, 1):
                price = (item.get("price") or "").strip()
                print(f"{i:>4}. {item.get('title', 'N/A')}")
                print(f"       Price    : {price + ' €' if price else 'N/A'}")
                print(f"       Published: {item.get('published_at') or 'N/A'}")
                print(f"       URL      : {item.get('url', 'N/A')}")

    except aiohttp.ClientConnectorError:
        print("ERROR: Could not connect. Is the server running?")
        print("  Start it with: uvicorn main:app")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


async def main() -> None:
    max_pages = (
        int(sys.argv[sys.argv.index("--max-pages") + 1])
        if "--max-pages" in sys.argv
        else 1
    )
    min_publish_date = (
        sys.argv[sys.argv.index("--min-publish-date") + 1]
        if "--min-publish-date" in sys.argv
        else None
    )

    async with aiohttp.ClientSession() as session:
        for search in SEARCHES:
            await run_search(session, search, max_pages, min_publish_date)

    print(f"\n{'=' * 60}\nDone.\n")


if __name__ == "__main__":
    asyncio.run(main())
