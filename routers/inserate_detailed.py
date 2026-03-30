"""
Combined endpoint router for fetching listings with detailed information.

This router provides the /inserate-detailed endpoint that combines listing search
and detail fetching in a single request, optimizing performance through concurrent
processing while maintaining comprehensive error handling for partial failures.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Request

from scrapers.inserate import get_inserate_klaz_optimized
from scrapers.inserat import get_inserate_details_optimized
from utils.browser import OptimizedPlaywrightManager
from utils.performance import PerformanceTracker, PageMetrics
from utils.error_handling import (
    ErrorClassifier,
    WarningManager,
    ErrorLogger,
    ErrorContext,
    ErrorSeverity,
    error_handling_context,
)

router = APIRouter()


def optimize_concurrent_detail_fetching(
    listing_count: int, max_concurrent_details: int, browser_contexts_available: int
) -> tuple[int, int]:
    """
    Optimize concurrent detail fetching parameters based on available resources.

    This function analyzes the number of listings to process and available browser
    contexts to determine optimal concurrency levels and batch sizes.

    Args:
        listing_count: Number of listings to process
        max_concurrent_details: Maximum requested concurrent detail fetches
        browser_contexts_available: Number of browser contexts available

    Returns:
        Tuple of (optimal_concurrency, batch_size)
    """
    # Ensure we don't exceed available browser contexts
    optimal_concurrency = min(
        max_concurrent_details,
        browser_contexts_available,
        listing_count,  # No point in more workers than listings
    )

    # For small numbers of listings, use lower concurrency to avoid overhead
    if listing_count <= 3:
        optimal_concurrency = min(optimal_concurrency, 2)
    elif listing_count <= 10:
        optimal_concurrency = min(optimal_concurrency, 3)

    # Calculate batch size for processing (useful for very large listing counts)
    if listing_count > 50:
        batch_size = 25  # Process in batches to manage memory
    elif listing_count > 20:
        batch_size = 15
    else:
        batch_size = listing_count  # Process all at once

    return optimal_concurrency, batch_size


async def fetch_listing_details_concurrent(
    browser_manager: OptimizedPlaywrightManager,
    listings: List[Dict[str, Any]],
    max_concurrent_details: int = 5,
) -> tuple[List[Dict[str, Any]], List[PageMetrics], List[str]]:
    """
    Optimized concurrent detail fetching for all listings found in search results.

    This function implements:
    - Controlled concurrency using semaphores to prevent resource exhaustion
    - Graceful handling of partial failures where some detail fetches fail
    - Comprehensive performance metrics for the combined operation
    - Retry logic with exponential backoff for failed detail fetches
    - Resource-efficient browser context management

    Args:
        browser_manager: OptimizedPlaywrightManager instance
        listings: List of listing dictionaries with 'adid' field
        max_concurrent_details: Maximum concurrent detail fetches

    Returns:
        Tuple of (detailed_listings, detail_metrics, warnings)
    """
    if not listings:
        return [], [], []

    # Create semaphore to limit concurrent detail fetches
    detail_semaphore = asyncio.Semaphore(max_concurrent_details)

    # Track performance metrics for the detail fetching phase
    detail_phase_start = time.time()

    async def fetch_single_detail_with_retry(
        listing: Dict[str, Any],
        index: int,
        max_retries: int = 2,
        warning_manager: WarningManager = None,
        logger: ErrorLogger = None,
    ) -> tuple[Optional[Dict[str, Any]], PageMetrics]:
        """
        Fetch details for a single listing with comprehensive error handling and retry logic.

        Implements exponential backoff retry strategy, structured error classification,
        and graceful failure handling to ensure partial failures don't impact the
        overall operation while providing detailed debugging information.
        """
        async with detail_semaphore:
            start_time = time.time()
            listing_id = listing.get("adid")
            listing_url = listing.get("url", "")

            if not listing_id:
                error_msg = f"Missing adid for listing at index {index}"

                # Add structured warning
                if warning_manager:
                    warning_manager.add_warning(
                        error_msg,
                        ErrorSeverity.MEDIUM,
                        ErrorContext(
                            operation="detail_fetch_validation",
                            page_number=index + 1,
                            url=listing_url,
                        ),
                        affected_items=[f"listing_{index}"],
                        impact_description="Cannot fetch details without valid listing ID",
                    )

                failed_metric = PageMetrics(
                    page_number=index + 1,
                    url=listing_url,
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    retry_count=0,
                    error_message=error_msg,
                    results_count=0,
                    error_category="validation",
                )
                return None, failed_metric

            last_structured_error = None

            # Retry loop with exponential backoff and structured error handling
            for attempt in range(max_retries + 1):
                try:
                    # Fetch detailed information using optimized function
                    detail_response = await get_inserate_details_optimized(
                        browser_manager,
                        listing_id,
                        retry_count=1,  # Internal retry in detail function
                    )

                    if detail_response["success"]:
                        # Successfully fetched details - combine with listing summary
                        combined_listing = {
                            **listing,  # Original listing data (title, price, description, etc.)
                            "details": detail_response["data"],  # Detailed information
                            "detail_fetch_time": round(time.time() - start_time, 3),
                            "detail_performance": detail_response.get(
                                "performance_metrics", {}
                            ),
                        }

                        # Check for warnings from the detail fetch
                        if detail_response.get("warnings"):
                            combined_listing["detail_warnings"] = detail_response[
                                "warnings"
                            ]

                        # Create successful metric with comprehensive information
                        success_metric = PageMetrics(
                            page_number=index + 1,
                            url=f"https://www.kleinanzeigen.de/s-anzeige/{listing_id}",
                            start_time=start_time,
                            end_time=time.time(),
                            success=True,
                            retry_count=attempt,
                            error_message=None,
                            results_count=1,
                            warning_count=len(detail_response.get("warnings", [])),
                        )

                        # Add success warning if retries were needed
                        if attempt > 0 and warning_manager:
                            warning_manager.add_warning(
                                f"Detail fetch for listing {listing_id} succeeded after {attempt} retries",
                                ErrorSeverity.LOW,
                                ErrorContext(
                                    operation="detail_fetch_retry_success",
                                    listing_id=listing_id,
                                    retry_attempt=attempt,
                                ),
                                affected_items=[listing_id],
                                impact_description="Temporary delays resolved, details successfully fetched",
                            )

                        return combined_listing, success_metric
                    else:
                        # Detail fetch failed - classify the error
                        error_message = detail_response.get(
                            "error", "Unknown error fetching details"
                        )
                        error_category = detail_response.get(
                            "error_category", "unknown"
                        )

                        # Create structured error for classification
                        error_context = ErrorContext(
                            operation="detail_fetch",
                            listing_id=listing_id,
                            retry_attempt=attempt,
                            url=f"https://www.kleinanzeigen.de/s-anzeige/{listing_id}",
                        )

                        # Use existing error information or classify
                        if error_category != "unknown":
                            last_structured_error = type(
                                "StructuredError",
                                (),
                                {
                                    "message": error_message,
                                    "category": type(
                                        "ErrorCategory", (), {"value": error_category}
                                    )(),
                                    "severity": type(
                                        "ErrorSeverity",
                                        (),
                                        {
                                            "value": detail_response.get(
                                                "error_severity", "medium"
                                            )
                                        },
                                    )(),
                                    "should_retry": lambda max_retries: attempt
                                    < max_retries
                                    and error_category
                                    in ["recoverable", "network", "resource"],
                                },
                            )()
                        else:
                            # Classify the error using our classifier
                            exception = Exception(error_message)
                            last_structured_error = ErrorClassifier.classify_exception(
                                exception, error_context, "detail_fetch"
                            )

                        # Check if we should retry
                        if attempt < max_retries and last_structured_error.should_retry(
                            max_retries
                        ):
                            import random

                            wait_time = (2**attempt) + random.uniform(0, 0.5)

                            # Add retry warning
                            if warning_manager:
                                warning_manager.add_warning(
                                    f"Retrying detail fetch for listing {listing_id} after {last_structured_error.category.value} error",
                                    ErrorSeverity.MEDIUM,
                                    error_context,
                                    affected_items=[listing_id],
                                    impact_description=f"Temporary delay of {wait_time:.1f}s before retry",
                                )

                            await asyncio.sleep(wait_time)
                            continue

                        # All retries exhausted
                        break

                except Exception as e:
                    # Classify unexpected exceptions
                    error_context = ErrorContext(
                        operation="detail_fetch_exception",
                        listing_id=listing_id,
                        retry_attempt=attempt,
                        url=f"https://www.kleinanzeigen.de/s-anzeige/{listing_id}",
                    )

                    last_structured_error = ErrorClassifier.classify_exception(
                        e, error_context, "detail_fetch"
                    )

                    # Log the error if logger is available
                    if logger:
                        logger.log_error(last_structured_error)

                    # Check if we should retry
                    if attempt < max_retries and last_structured_error.should_retry(
                        max_retries
                    ):
                        import random

                        wait_time = (2**attempt) + random.uniform(0, 0.5)

                        # Add retry warning
                        if warning_manager:
                            warning_manager.add_warning(
                                f"Retrying detail fetch for listing {listing_id} after exception",
                                ErrorSeverity.MEDIUM,
                                error_context,
                                affected_items=[listing_id],
                                impact_description=f"Temporary delay of {wait_time:.1f}s before retry",
                            )

                        await asyncio.sleep(wait_time)
                        continue

                    # All retries exhausted
                    break

            # All retries exhausted - create comprehensive failed metric
            if last_structured_error:
                error_msg = f"Failed after {max_retries + 1} attempts: {last_structured_error.message}"
                error_category = last_structured_error.category.value

                # Add final failure warning
                if warning_manager:
                    warning_manager.add_warning(
                        f"Detail fetch permanently failed for listing {listing_id}",
                        ErrorSeverity.HIGH
                        if last_structured_error.category.value == "non_recoverable"
                        else ErrorSeverity.MEDIUM,
                        ErrorContext(
                            operation="detail_fetch_final_failure",
                            listing_id=listing_id,
                            retry_attempt=max_retries,
                        ),
                        affected_items=[listing_id],
                        impact_description=f"Details unavailable due to {last_structured_error.category.value} error",
                    )
            else:
                error_msg = f"Failed after {max_retries + 1} attempts: Unknown error"
                error_category = "unknown"

            failed_metric = PageMetrics(
                page_number=index + 1,
                url=f"https://www.kleinanzeigen.de/s-anzeige/{listing_id}",
                start_time=start_time,
                end_time=time.time(),
                success=False,
                retry_count=max_retries,
                error_message=error_msg,
                results_count=0,
                error_category=error_category,
            )

            return None, failed_metric

    # Initialize warning manager and logger for detail fetching
    detail_warning_manager = WarningManager()
    detail_logger = ErrorLogger("detail_fetcher")

    # Create tasks for all detail fetches with comprehensive error handling
    detail_tasks = [
        fetch_single_detail_with_retry(
            listing, i, warning_manager=detail_warning_manager, logger=detail_logger
        )
        for i, listing in enumerate(listings)
    ]

    # Execute all detail fetches concurrently with comprehensive error handling
    detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)

    # Process results with comprehensive error tracking and structured warnings
    detailed_listings = []
    detail_metrics = []
    successful_fetches = 0
    failed_fetches = 0

    for i, result in enumerate(detail_results):
        if isinstance(result, Exception):
            # Handle unexpected exceptions that weren't caught by retry logic
            failed_fetches += 1

            # Classify the unexpected exception
            error_context = ErrorContext(
                operation="detail_fetch_gather_exception",
                page_number=i + 1,
                listing_id=listings[i].get("adid", f"unknown_{i}"),
                url=listings[i].get("url", ""),
            )

            structured_error = ErrorClassifier.classify_exception(
                result, error_context, "concurrent_detail_fetch"
            )

            # Add to warning manager
            detail_warning_manager.add_error_as_warning(
                structured_error,
                affected_items=[listings[i].get("adid", f"listing_{i + 1}")],
                impact_description=f"Details unavailable for listing {i + 1} due to unexpected error",
            )

            # Log the error
            detail_logger.log_error(structured_error)

            # Create failed metric with enhanced information
            failed_metric = PageMetrics(
                page_number=i + 1,
                url=listings[i].get("url", ""),
                start_time=time.time(),
                end_time=time.time(),
                success=False,
                retry_count=0,
                error_message=structured_error.message,
                results_count=0,
                error_category=structured_error.category.value,
            )
            detail_metrics.append(failed_metric)
        else:
            detailed_listing, metric = result
            detail_metrics.append(metric)

            if detailed_listing is not None:
                detailed_listings.append(detailed_listing)
                successful_fetches += 1

                # Check for warnings in successful fetches
                if metric.warning_count > 0:
                    detail_warning_manager.add_warning(
                        f"Detail fetch for listing {listings[i].get('adid', i + 1)} completed with warnings",
                        ErrorSeverity.LOW,
                        ErrorContext(
                            operation="detail_fetch_with_warnings",
                            listing_id=listings[i].get("adid"),
                            page_number=i + 1,
                        ),
                        affected_items=[listings[i].get("adid", f"listing_{i + 1}")],
                        impact_description="Details fetched but with minor issues",
                    )
            else:
                failed_fetches += 1
                # The warning was already added by fetch_single_detail_with_retry

    # Calculate detail phase performance summary
    detail_phase_duration = time.time() - detail_phase_start
    success_rate = (successful_fetches / len(listings)) * 100 if listings else 0

    # Add operation-level warnings based on overall performance
    if failed_fetches > 0:
        if success_rate < 50:
            detail_warning_manager.add_warning(
                f"High detail fetch failure rate: Only {successful_fetches}/{len(listings)} succeeded ({success_rate:.1f}%)",
                ErrorSeverity.HIGH,
                ErrorContext(
                    operation="detail_fetch_summary",
                    concurrent_operations=max_concurrent_details,
                ),
                affected_items=["detail_phase"],
                impact_description="Significant data loss in detail fetching phase",
            )
        elif failed_fetches > 1:
            detail_warning_manager.add_warning(
                f"Partial detail fetch success: {failed_fetches} out of {len(listings)} failed",
                ErrorSeverity.MEDIUM,
                ErrorContext(
                    operation="detail_fetch_summary",
                    concurrent_operations=max_concurrent_details,
                ),
                affected_items=["detail_phase"],
                impact_description="Some listing details unavailable",
            )

    # Add performance warnings
    if detail_phase_duration > 15.0:
        detail_warning_manager.add_warning(
            f"Slow detail fetching: {detail_phase_duration:.1f}s for {len(listings)} listings",
            ErrorSeverity.MEDIUM,
            ErrorContext(
                operation="detail_fetch_performance",
                concurrent_operations=max_concurrent_details,
            ),
            impact_description="Detail fetching performance below optimal levels",
        )

    # Log comprehensive operation summary
    detail_logger.log_operation_summary(
        operation=f"concurrent_detail_fetch_{len(listings)}_listings",
        total_items=len(listings),
        successful_items=successful_fetches,
        warnings=detail_warning_manager.get_warnings(),
        errors=[],  # Errors were converted to warnings for partial failure handling
        duration=detail_phase_duration,
    )

    # Log performance summary for debugging
    print(
        f"[INFO] Detail fetching completed: {successful_fetches}/{len(listings)} successful "
        f"({success_rate:.1f}%) in {detail_phase_duration:.2f}s with {max_concurrent_details} concurrent workers"
    )

    # Return comprehensive results with structured warnings
    return (
        detailed_listings,
        detail_metrics,
        detail_warning_manager.get_user_friendly_messages(),
    )


@router.get("/inserate-detailed")
async def get_inserate_with_details(
    request: Request,
    query: str = Query(None, description="Search query string"),
    location: str = Query(None, description="Location filter"),
    radius: int = Query(None, description="Search radius in kilometers"),
    min_price: int = Query(None, description="Minimum price filter"),
    max_price: int = Query(None, description="Maximum price filter"),
    page_count: int = Query(1, ge=1, le=3, description="Number of pages to fetch"),
    max_concurrent_details: int = Query(
        5, ge=1, le=10, description="Maximum concurrent detail fetches"
    ),
):
    """
    Enhanced combined endpoint with comprehensive error handling and warnings.

    This endpoint performs two phases with detailed error tracking:
    1. Fetch listings using the optimized search functionality
    2. Concurrently fetch detailed information for each listing found

    The response includes both summary and detailed information in a unified format,
    with comprehensive performance metrics, structured error categorization,
    and graceful handling of partial failures with detailed warnings.

    Args:
        query: Search query string
        location: Location filter
        radius: Search radius in kilometers
        min_price: Minimum price filter
        max_price: Maximum price filter
        page_count: Number of pages to fetch (1-20)
        max_concurrent_details: Maximum concurrent detail fetches (1-10)

    Returns:
        Combined response with listings, details, performance metrics, and comprehensive warnings
    """
    # Initialize comprehensive error handling and performance tracking
    logger = ErrorLogger("combined_endpoint")

    with error_handling_context(
        operation="combined_inserate_detailed_request", logger=logger
    ) as error_ctx:
        # Validate input parameters
        if page_count > 20:
            error_ctx.add_warning(
                f"Page count {page_count} exceeds recommended maximum of 20",
                ErrorSeverity.MEDIUM,
                impact_description="High page counts may result in slower response times and higher failure rates",
            )

        if max_concurrent_details > 10:
            error_ctx.add_warning(
                f"Concurrent detail fetches {max_concurrent_details} exceeds recommended maximum of 10",
                ErrorSeverity.MEDIUM,
                impact_description="High concurrency may overwhelm server resources",
            )

        # Use shared browser manager from app state
        browser_manager = request.app.state.browser_manager

        # Initialize performance tracking for the entire operation
        tracker = PerformanceTracker()
        tracker.start_request()

        try:
            # Phase 1: Fetch listings
            listings_response = await get_inserate_klaz_optimized(
                browser_manager,
                query,
                location,
                radius,
                min_price,
                max_price,
                page_count,
            )

            if not listings_response["success"]:
                return {
                    "success": False,
                    "error": "Failed to fetch listings",
                    "phase": "listing_search",
                    "data": [],
                    "time_taken": listings_response["time_taken"],
                    "performance_metrics": listings_response["performance_metrics"],
                }

            listings = listings_response["results"]

            # If no listings found, return early
            if not listings:
                # Add listing search metrics to tracker
                for page_metric in listings_response["performance_metrics"][
                    "page_details"
                ]:
                    metric = PageMetrics(
                        page_number=page_metric["page_number"],
                        url="",  # URL not available in the response format
                        start_time=time.time() - page_metric["time_taken"],
                        end_time=time.time(),
                        success=page_metric["success"],
                        retry_count=page_metric["retry_count"],
                        error_message=page_metric.get("error"),
                        results_count=page_metric["results_count"],
                    )
                    tracker.add_page_metric(metric)

                # Set browser and concurrency metrics
                tracker.set_browser_contexts_used(
                    listings_response.get("browser_metrics", {}).get(
                        "contexts_in_use", 0
                    )
                )
                tracker.set_concurrent_level(
                    listings_response["performance_metrics"]["concurrent_level"]
                )

                final_metrics = tracker.get_request_metrics()

                return {
                    "success": True,
                    "data": [],
                    "unique_results": 0,
                    "time_taken": round(final_metrics.total_time, 3),
                    "performance_metrics": {
                        **final_metrics.to_dict(),
                        "listing_phase": listings_response["performance_metrics"],
                        "detail_phase": {
                            "pages_requested": 0,
                            "pages_successful": 0,
                            "pages_failed": 0,
                            "concurrent_level": 0,
                            "page_details": [],
                        },
                    },
                    "browser_metrics": listings_response.get("browser_metrics", {}),
                    "warnings": listings_response.get("warnings", []),
                }

            # Phase 2: Optimize and fetch detailed information for all listings concurrently
            browser_metrics = browser_manager.get_performance_metrics()
            available_contexts = (
                browser_metrics["contexts_in_pool"]
                + browser_metrics["max_contexts"]
                - browser_metrics["contexts_in_use"]
            )

            # Optimize concurrent processing parameters
            optimal_concurrency, batch_size = optimize_concurrent_detail_fetching(
                len(listings), max_concurrent_details, available_contexts
            )

            print(
                f"[INFO] Optimized detail fetching: {len(listings)} listings, "
                f"{optimal_concurrency} concurrent workers, batch size {batch_size}"
            )

            (
                detailed_listings,
                detail_metrics,
                detail_warnings,
            ) = await fetch_listing_details_concurrent(
                browser_manager, listings, optimal_concurrency
            )

            # Combine all metrics
            # Add listing search metrics
            for page_metric in listings_response["performance_metrics"]["page_details"]:
                metric = PageMetrics(
                    page_number=page_metric["page_number"],
                    url="",  # URL not available in the response format
                    start_time=time.time() - page_metric["time_taken"],
                    end_time=time.time(),
                    success=page_metric["success"],
                    retry_count=page_metric["retry_count"],
                    error_message=page_metric.get("error"),
                    results_count=page_metric["results_count"],
                )
                tracker.add_page_metric(metric)

            # Add detail fetch metrics
            for detail_metric in detail_metrics:
                tracker.add_page_metric(detail_metric)

            # Set browser and concurrency metrics
            browser_metrics = browser_manager.get_performance_metrics()
            tracker.set_browser_contexts_used(
                browser_metrics["contexts_in_use"] + browser_metrics["contexts_in_pool"]
            )
            tracker.set_concurrent_level(
                max(
                    listings_response["performance_metrics"]["concurrent_level"],
                    max_concurrent_details,
                )
            )

            # Generate final metrics
            final_metrics = tracker.get_request_metrics()

            # Combine warnings
            all_warnings = []
            if listings_response.get("warnings"):
                all_warnings.extend(listings_response["warnings"])
            if detail_warnings:
                all_warnings.extend(detail_warnings)

            # Calculate detail success metrics
            detail_success_count = len(detailed_listings)
            detail_total_count = len(listings)
            detail_success_rate = (
                (detail_success_count / detail_total_count * 100)
                if detail_total_count > 0
                else 0
            )

            # Add operation-level warnings for detail phase
            if detail_success_rate < 80 and detail_total_count > 0:
                error_ctx.add_warning(
                    f"Low detail fetch success rate: {detail_success_count}/{detail_total_count} ({detail_success_rate:.1f}%)",
                    ErrorSeverity.MEDIUM,
                    impact_description="Some listing details are unavailable",
                )

            # Prepare comprehensive response
            response = {
                "success": True,
                "data": detailed_listings,
                "unique_results": len(detailed_listings),
                "time_taken": round(final_metrics.total_time, 3),
                "performance_metrics": {
                    **final_metrics.to_dict(),
                    "listing_phase": {
                        "pages_requested": listings_response["performance_metrics"][
                            "pages_requested"
                        ],
                        "pages_successful": listings_response["performance_metrics"][
                            "pages_successful"
                        ],
                        "pages_failed": listings_response["performance_metrics"][
                            "pages_failed"
                        ],
                        "concurrent_level": listings_response["performance_metrics"][
                            "concurrent_level"
                        ],
                        "page_details": listings_response["performance_metrics"][
                            "page_details"
                        ],
                    },
                    "detail_phase": {
                        "listings_requested": detail_total_count,
                        "listings_successful": detail_success_count,
                        "listings_failed": detail_total_count - detail_success_count,
                        "success_rate": detail_success_rate,
                        "concurrent_level": optimal_concurrency,
                        "detail_metrics": [
                            metric.to_dict() for metric in detail_metrics
                        ],
                    },
                },
                "browser_metrics": browser_manager.get_performance_metrics(),
            }

            # Add warnings if any exist
            if all_warnings:
                response["warnings"] = all_warnings
                response["partial_success"] = len(all_warnings) > 0

            # Log successful operation summary
            logger.log_operation_summary(
                operation="combined_inserate_detailed_endpoint",
                total_items=detail_total_count,
                successful_items=detail_success_count,
                warnings=error_ctx.warnings.get_warnings(),
                errors=[],
                duration=final_metrics.total_time,
            )

            return response

        except HTTPException:
            # Re-raise HTTP exceptions (already handled above)
            raise
        except Exception as e:
            # Handle unexpected critical errors with comprehensive error handling
            structured_error = error_ctx.handle_exception(e, "combined_endpoint")

            try:
                # Try to get partial metrics if available
                final_metrics = tracker.get_request_metrics()
                browser_metrics = browser_manager.get_performance_metrics()

                # Log the critical error
                logger.log_error(structured_error)

                return {
                    "success": False,
                    "error": structured_error.message,
                    "error_category": structured_error.category.value,
                    "error_severity": structured_error.severity.value,
                    "recovery_suggestions": structured_error.recovery_suggestions,
                    "data": [],
                    "unique_results": 0,
                    "time_taken": round(final_metrics.total_time, 3),
                    "performance_metrics": final_metrics.to_dict(),
                    "browser_metrics": browser_metrics,
                    "warnings": error_ctx.warnings.get_user_friendly_messages(),
                }
            except Exception:
                # Fallback response if metrics collection also fails
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": structured_error.message,
                        "category": structured_error.category.value,
                        "severity": structured_error.severity.value,
                        "recovery_suggestions": structured_error.recovery_suggestions,
                    },
                )

        except HTTPException:
            # Re-raise HTTP exceptions (already handled above)
            raise
        except Exception as e:
            # Handle unexpected critical errors with comprehensive error handling
            structured_error = error_ctx.handle_exception(e, "combined_endpoint")

            try:
                # Try to get partial metrics if available
                final_metrics = tracker.get_request_metrics()
                browser_metrics = browser_manager.get_performance_metrics()

                # Log the critical error
                logger.log_error(structured_error)

                return {
                    "success": False,
                    "error": structured_error.message,
                    "error_category": structured_error.category.value,
                    "error_severity": structured_error.severity.value,
                    "recovery_suggestions": structured_error.recovery_suggestions,
                    "data": [],
                    "unique_results": 0,
                    "time_taken": round(final_metrics.total_time, 3),
                    "performance_metrics": final_metrics.to_dict(),
                    "browser_metrics": browser_metrics,
                    "warnings": error_ctx.warnings.get_user_friendly_messages(),
                }
            except Exception:
                # Fallback response if metrics collection also fails
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": structured_error.message,
                        "category": structured_error.category.value,
                        "severity": structured_error.severity.value,
                        "recovery_suggestions": structured_error.recovery_suggestions,
                    },
                )

        finally:
            # Browser manager is shared and managed by the application lifecycle
            pass
