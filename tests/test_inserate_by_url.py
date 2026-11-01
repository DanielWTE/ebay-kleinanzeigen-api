"""
Fetch listings via POST /inserate-by-url using pre-configured Kleinanzeigen URLs.

URLs are loaded from tests/inserate_urls.json — add entries there to extend coverage.

Usage:
  python tests/test_inserate_by_url.py               # all URLs, 1 page each
  python tests/test_inserate_by_url.py --max-pages 3
"""

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

BASE_URL = "http://localhost:8000"
URLS_FILE = Path(__file__).parent / "inserate_urls.json"


def load_searches() -> list:
    with URLS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


async def run_search(
    session: aiohttp.ClientSession, search: dict, max_pages: int
) -> None:
    print(f"\n{'=' * 60}")
    print(f"Search: {search['label']}")
    print(f"URL:    {search['url']}")
    print(f"{'=' * 60}")

    payload = {"url": search["url"], "max_pages": max_pages}

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
                print(f"       Price: {price + ' €' if price else 'N/A'}")
                print(f"       URL:   {item.get('url', 'N/A')}")

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

    searches = load_searches()
    print(f"Loaded {len(searches)} search(es) from {URLS_FILE}")

    async with aiohttp.ClientSession() as session:
        for search in searches:
            await run_search(session, search, max_pages)

    print(f"\n{'=' * 60}\nDone.\n")


if __name__ == "__main__":
    asyncio.run(main())
