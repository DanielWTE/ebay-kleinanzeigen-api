from scrapers.inserat import get_inserate_details_optimized
from fastapi import APIRouter, HTTPException, Request, Query
from schemas import ErrorResponse, ListingDetailResponse, ListingNotFoundResponse

router = APIRouter()


@router.get(
    "/inserat/{id}",
    response_model=ListingDetailResponse,
    response_model_exclude_unset=True,
    responses={
        400: {"model": ErrorResponse, "description": "Blank listing ID"},
        404: {"model": ListingNotFoundResponse, "description": "Ad not found or deleted"},
        500: {"model": ErrorResponse, "description": "Failed to fetch listing details"},
        503: {"model": ErrorResponse, "description": "Browser manager not initialized"},
    },
)
async def get_inserat(
    request: Request,
    id: str,
    batch_id: str = Query(
        ..., description="Client-supplied ID to correlate multiple calls in server logs"
    ),
):
    """
    Fetch detailed information for a specific listing.

    Retrieves comprehensive details including description, seller information,
    location, pricing, and other metadata for the specified listing ID.

    Pass batch_id to correlate multiple sequential calls in server logs:
      GET /inserat/123?batch_id=my-session
    """
    if not id or not id.strip():
        raise HTTPException(status_code=400, detail="Invalid listing ID")

    browser_manager = request.app.state.browser_manager
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")

    try:
        response = await get_inserate_details_optimized(
            browser_manager, id, request_id=batch_id
        )

        if not response.get("success", False):
            if response.get("not_found"):
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "Ad not found or has been deleted",
                        "status": "deleted",
                    },
                )
            raise HTTPException(
                status_code=500, detail="Failed to fetch listing details"
            )

        # Clean response - keep only essential data
        clean_response = {
            "success": response["success"],
            "time_taken": response["time_taken"],
            "data": response["data"],
        }

        # Add minimal performance metrics
        if "performance_metrics" in response:
            metrics = response["performance_metrics"]
            clean_response["performance_metrics"] = {
                "success_rate": metrics.get("success_rate", 100),
                "time_taken": metrics.get("average_page_time", response["time_taken"]),
            }

        return clean_response

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
