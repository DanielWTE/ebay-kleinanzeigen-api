from urllib.parse import urlencode

from fastapi import HTTPException

from utils.browser import PlaywrightManager


async def get_inserate_klaz(browser_manager: PlaywrightManager,
                            query: str = None,
                            location: str = None,
                            radius: int = None,
                            min_price: int = None,
                            max_price: int = None,
                            page_count: int = 1):
    base_url = "https://www.kleinanzeigen.de"

    # Build the price filter part of the path
    price_path = ""
    if min_price is not None or max_price is not None:
        # Convert prices to strings; if one is None, leave its place empty
        min_price_str = str(min_price) if min_price is not None else ""
        max_price_str = str(max_price) if max_price is not None else ""
        price_path = f"/preis:{min_price_str}:{max_price_str}"

    # Build the search path with price and page information
    search_path = f"{price_path}/s-seite"
    search_path += ":{page}"

    # Build query parameters as before
    params = {}
    if query:
        params['keywords'] = query
    if location:
        params['locationStr'] = location
    if radius:
        params['radius'] = radius

    # Construct the full URL and get it
    search_url = base_url + search_path + ("?" + urlencode(params) if params else "")

    page = await browser_manager.new_context_page()
    try:
        await page.goto(search_url.format(page=1), timeout=120000)
        results = []

        for i in range(page_count):
            page_results = await get_ads(page)
            results.extend(page_results)

            if i < page_count - 1:
                try:
                    await page.goto(search_url.format(page=i+2), timeout=120000)
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"Failed to load page {i + 2}: {str(e)}")
                    break
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await browser_manager.close_page(page)


async def get_ads(page):
    try:
        items = await page.query_selector_all(".ad-listitem:not(.is-topad):not(.badge-hint-pro-small-srp)")
        results = []
        for item in items:
            article = await item.query_selector("article")
            if article:
                data_adid = await article.get_attribute("data-adid")
                data_href = await article.get_attribute("data-href")
                # Get title from h2 element
                title_element = await article.query_selector("h2.text-module-begin a.ellipsis")
                title_text = await title_element.inner_text() if title_element else ""
                # Get price and description
                price = await article.query_selector("p.aditem-main--middle--price-shipping--price")
                # strip € and VB and strip whitespace
                price_text = await price.inner_text() if price else ""
                price_text = price_text.replace("€", "").replace("VB", "").replace(".", "").strip()
                description = await article.query_selector("p.aditem-main--middle--description")
                description_text = await description.inner_text() if description else ""
                if data_adid and data_href:
                    data_href = f"https://www.kleinanzeigen.de{data_href}"
                    results.append({"adid": data_adid, "url": data_href, "title": title_text, "price": price_text, "description": description_text})
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
