from scrapers.inserate import get_inserate_klaz
from fastapi import APIRouter, Query
from utils.browser import PlaywrightManager

router = APIRouter()

@router.get("/inserate")
async def get_inserate(page_count: int = Query(1, ge=1, le=20)):
    browser_manager = PlaywrightManager()
    await browser_manager.start()
    try:
        results = await get_inserate_klaz(browser_manager, page_count)
        return {"success": True, "data": results}
    finally:
        await browser_manager.close() 