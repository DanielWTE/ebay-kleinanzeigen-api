from fastapi import HTTPException
from utils.browser import PlaywrightManager

async def get_inserate_klaz(browser_manager: PlaywrightManager, page_count: int):
    page = await browser_manager.new_context_page()
    try:
        await page.goto("https://www.kleinanzeigen.de/s-seite:1", timeout=120000)
        results = []
        
        for i in range(page_count):
            page_results = await get_ads(page)
            results.extend(page_results)
            
            if i < page_count - 1:
                next_page_url = f"https://www.kleinanzeigen.de/s-seite:{i+2}"
                try:
                    await page.goto(next_page_url, timeout=120000)
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"Failed to load page {i+2}: {str(e)}")
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
                if data_adid and data_href:
                    data_href = f"https://www.kleinanzeigen.de{data_href}"
                    results.append({"adid": data_adid, "url": data_href})
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 