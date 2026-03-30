from fastapi import APIRouter, Query, HTTPException, Request
from scrapers.inserate import get_inserate_klaz_optimized
from utils.error_handling import ErrorLogger, error_handling_context, ErrorSeverity

router = APIRouter()


@router.get("/inserate")
async def get_inserate(
    request: Request,
    query: str = Query(None),
    location: str = Query(None),
    radius: int = Query(None),
    min_price: int = Query(None),
    max_price: int = Query(None),
    page_count: int = Query(1, ge=1, le=20),
):
    """
    Enhanced inserate endpoint with comprehensive error handling and warnings.

    This endpoint fetches listings with improved error categorization, detailed
    warnings for partial failures, and comprehensive logging for debugging.
    """
    logger = ErrorLogger("inserate_router")

    with error_handling_context(
        operation="inserate_api_request", logger=logger
    ) as error_ctx:
        # Use shared browser manager from app state
        browser_manager = request.app.state.browser_manager

        try:
            # Validate input parameters
            if page_count > 20:
                error_ctx.add_warning(
                    f"Page count {page_count} exceeds recommended maximum of 20",
                    ErrorSeverity.MEDIUM,
                    impact_description="High page counts may result in slower response times",
                )

            # Use optimized scraper function
            response = await get_inserate_klaz_optimized(
                browser_manager,
                query,
                location,
                radius,
                min_price,
                max_price,
                page_count,
            )

            # Handle scraper errors
            if not response.get("success", False):
                error_message = response.get("error", "Unknown scraper error")
                error_category = response.get("error_category", "unknown")
                error_severity = response.get("error_severity", "medium")
                recovery_suggestions = response.get("recovery_suggestions", [])

                # Log the error for debugging
                logger.logger.error(
                    f"Scraper failed: {error_message} (Category: {error_category})"
                )

                # Return structured error response
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": error_message,
                        "category": error_category,
                        "severity": error_severity,
                        "recovery_suggestions": recovery_suggestions,
                        "performance_metrics": response.get("performance_metrics", {}),
                        "warnings": response.get("warnings", []),
                    },
                )

            # Remove duplicates based on 'adid' while maintaining backward compatibility
            seen_adids = set()
            unique_results = []
            duplicate_count = 0

            for result in response["results"]:
                if result["adid"] not in seen_adids:
                    unique_results.append(result)
                    seen_adids.add(result["adid"])
                else:
                    duplicate_count += 1

            # Add warning if significant duplicates were found
            if duplicate_count > 0:
                error_ctx.add_warning(
                    f"Removed {duplicate_count} duplicate listings",
                    ErrorSeverity.LOW,
                    impact_description=f"Duplicate removal reduced results from {len(response['results'])} to {len(unique_results)}",
                )

            # Prepare enhanced response with comprehensive error handling information
            enhanced_response = {
                "success": response["success"],
                "time_taken": response["time_taken"],
                "unique_results": len(unique_results),
                "data": unique_results,
                "performance_metrics": response["performance_metrics"],
                "browser_metrics": response.get("browser_metrics", {}),
            }

            # Combine warnings from scraper and router
            all_warnings = []
            router_warnings = error_ctx.warnings.get_user_friendly_messages()
            scraper_warnings = response.get("warnings", [])

            if router_warnings:
                all_warnings.extend(router_warnings)
            if scraper_warnings:
                all_warnings.extend(scraper_warnings)

            if all_warnings:
                enhanced_response["warnings"] = all_warnings

                # Add detailed warning information if available
                if response.get("detailed_warnings"):
                    enhanced_response["detailed_warnings"] = response[
                        "detailed_warnings"
                    ]
                if response.get("warning_summary"):
                    enhanced_response["warning_summary"] = response["warning_summary"]

                # Indicate partial success if there were warnings
                enhanced_response["partial_success"] = response.get(
                    "partial_success", False
                )

            # Add duplicate removal information
            if duplicate_count > 0:
                enhanced_response["duplicates_removed"] = duplicate_count
                enhanced_response["original_result_count"] = len(response["results"])

            # Log successful operation summary
            logger.log_operation_summary(
                operation="inserate_endpoint",
                total_items=page_count,
                successful_items=response["performance_metrics"].get(
                    "pages_successful", 0
                ),
                warnings=error_ctx.warnings.get_warnings(),
                errors=[],
                duration=response["time_taken"],
            )

            return enhanced_response

        except HTTPException:
            # Re-raise HTTP exceptions (already handled above)
            raise
        except Exception as e:
            # Handle unexpected errors
            structured_error = error_ctx.handle_exception(e, "inserate_endpoint")

            # Log the error
            logger.log_error(structured_error)

            raise HTTPException(
                status_code=500,
                detail={
                    "error": structured_error.message,
                    "category": structured_error.category.value,
                    "severity": structured_error.severity.value,
                    "recovery_suggestions": structured_error.recovery_suggestions,
                },
            )
