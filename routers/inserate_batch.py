import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from schemas import BatchResponse, ErrorResponse
from scrapers.inserat import get_inserate_details_optimized

router = APIRouter()


class InsérateBatchRequest(BaseModel):
    ids: list[str]
    max_concurrent: int = 1


@router.post(
    "/inserate/batch",
    response_model=BatchResponse,
    response_model_exclude_unset=True,
    responses={
        400: {"model": ErrorResponse, "description": "No valid listing IDs provided"},
        503: {"model": ErrorResponse, "description": "Browser manager not initialized"},
    },
)
async def get_inserate_batch(request: Request, body: InsérateBatchRequest):
    """
    Fetch detailed information for a list of listing IDs in a single request.

    All sub-fetches share one request ID so they can be correlated in the logs:
      [DETAIL req-a1b2c3d4 3/47] Fetching ad 3379172637: https://...

    max_concurrent controls how many detail pages are opened in parallel
    (default 1 = fully sequential, safest for bot-detection avoidance).
    """
    browser_manager = request.app.state.browser_manager
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")

    ids = [i.strip() for i in body.ids if i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid listing IDs provided")

    request_id = f"req-{uuid.uuid4().hex[:8]}"
    total = len(ids)
    semaphore = asyncio.Semaphore(max(1, body.max_concurrent))

    async def fetch_one(listing_id: str, pos: int):
        async with semaphore:
            return await get_inserate_details_optimized(
                browser_manager,
                listing_id,
                request_id=request_id,
                progress=f"{pos}/{total}",
            )

    tasks = [fetch_one(lid, i + 1) for i, lid in enumerate(ids)]
    raw = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[dict] = []
    errors: list[str] = []
    for lid, outcome in zip(ids, raw):
        if isinstance(outcome, Exception):
            errors.append(f"{lid}: {outcome}")
        elif outcome.get("success"):
            results.append(outcome["data"])
        else:
            errors.append(f"{lid}: {outcome.get('error', 'unknown error')}")

    return {
        "success": True,
        "request_id": request_id,
        "total": total,
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        **({"errors": errors} if errors else {}),
    }
