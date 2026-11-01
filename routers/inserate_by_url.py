from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class InserateByUrlRequest(BaseModel):
    url: str
    max_pages: int = 1
    min_publish_date: datetime | None = None


@router.post("/inserate-by-url")
async def inserate_by_url(request: Request, body: InserateByUrlRequest):
    """
    Scrape Kleinanzeigen listings using a full URL with all filters pre-configured.

    Pass any Kleinanzeigen search/category URL — all filters encoded in the URL
    (category, brand, year, fuel type, transmission, etc.) are preserved as-is.
    Page numbers are injected automatically for multi-page fetching.
    """
    browser_manager = request.app.state.browser_manager
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")

    from scrapers.inserate_by_url import scrape_by_url

    try:
        return await scrape_by_url(
            browser_manager=browser_manager,
            base_url=body.url,
            max_pages=body.max_pages,
            min_publish_date=body.min_publish_date,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
