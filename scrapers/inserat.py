from fastapi import HTTPException
from libs.websites import kleinanzeigen as lib
import re
import time
from utils.browser import OptimizedPlaywrightManager
from utils.performance import PageMetrics
from utils.error_handling import (
    WarningManager,
    ErrorLogger,
    ErrorSeverity,
    error_handling_context,
)


async def get_inserate_details(url: str, page):
    try:
        await page.goto(url, timeout=120000)

        try:
            await page.wait_for_selector(
                "#viewad-cntr-num", state="visible", timeout=2500
            )
        except Exception as e:
            print(f"[WARNING] Views element did not appear within 5 seconds: {e}")

        ad_id = await lib.get_element_content(
            page,
            "#viewad-ad-id-box > ul > li:nth-child(2)",
            default="[ERROR] Ad ID not found",
        )
        categories = [
            cat.strip()
            for cat in await lib.get_elements_content(page, ".breadcrump-link")
            if cat.strip()
        ]
        title = await lib.get_element_content(
            page, "#viewad-title", default="[ERROR] Title not found"
        )

        # Extract status from title element
        status = "active"  # Default status
        title_element = await page.query_selector("#viewad-title")
        if title_element:
            title_text = await title_element.inner_text()

            # Check for specific status indicators in the title text
            if "Verkauft" in title_text:
                status = "sold"
            elif "Reserviert •" in title_text:
                status = "reserved"
            elif "Gelöscht •" in title_text:
                status = "deleted"

            # Additional check for sold class
            title_classes = await title_element.get_attribute("class")
            if title_classes and "is-sold" in title_classes:
                status = "sold"

        # Final check for sold status in the page content
        sold_badge = await page.query_selector(".badge-sold")
        if sold_badge:
            status = "sold"

        price_element = await lib.get_element_content(page, "#viewad-price")
        price = lib.parse_price(price_element)
        views = await lib.get_element_content(page, "#viewad-cntr-num")
        description = await lib.get_element_content(page, "#viewad-description-text")
        if description:
            description = re.sub(r"[ \t]+", " ", description).strip()
            description = re.sub(r"\n+", "\n", description)

        images = await lib.get_image_sources(page, "#viewad-image")
        seller_details = await lib.get_seller_details(page)
        details = (
            await lib.get_details(page)
            if await page.query_selector("#viewad-details")
            else {}
        )
        features = (
            await lib.get_features(page)
            if await page.query_selector("#viewad-configuration")
            else {}
        )

        shipping_text = await lib.get_element_content(
            page, ".boxedarticle--details--shipping"
        )
        shipping = None
        if shipping_text:
            if "Nur Abholung" in shipping_text:
                shipping = "pickup"
            elif "Versand" in shipping_text:
                shipping = "shipping"

        location = await lib.get_location(page)
        extra_info = await lib.get_extra_info(page)

        return {
            "id": ad_id,
            "categories": categories,
            "title": title.split(" • ")[-1].strip()
            if " • " in title
            else title.strip(),
            "status": status,
            "price": price,
            "delivery": shipping,
            "location": location,
            "views": views if views else "0",
            "description": description,
            "images": images,
            "details": details,
            "features": features,
            "seller": seller_details,
            "extra_info": extra_info,
        }
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_inserate_details_optimized(
    browser_manager: OptimizedPlaywrightManager, listing_id: str, retry_count: int = 2
) -> dict:
    """
    Optimized version of get_inserate_details with comprehensive error handling and performance tracking.

    Args:
        browser_manager: OptimizedPlaywrightManager instance
        listing_id: The listing ID to fetch details for
        retry_count: Maximum number of retries (default: 2)

    Returns:
        Dictionary containing listing details, performance metrics, and warnings
    """
    from utils.performance import PerformanceTracker

    # Initialize error handling and performance tracking
    logger = ErrorLogger("inserat_scraper")
    warning_manager = WarningManager()
    tracker = PerformanceTracker()
    tracker.start_request()

    url = f"https://www.kleinanzeigen.de/s-anzeige/{listing_id}"

    with error_handling_context(
        operation="fetch_listing_details", listing_id=listing_id, url=url, logger=logger
    ) as error_ctx:
        last_structured_error = None

        for attempt in range(retry_count + 1):  # +1 for initial attempt
            start_time = time.time()

            try:
                # Use semaphore-controlled execution
                async def fetch_operation():
                    context = await browser_manager.get_context()
                    page = None
                    try:
                        page = await context.new_page()

                        # Get listing details using existing function
                        details = await get_inserate_details(url, page)

                        # Validate the extracted details
                        if not details or not details.get("id"):
                            warning_manager.add_warning(
                                f"Incomplete data extracted for listing {listing_id}",
                                ErrorSeverity.MEDIUM,
                                error_ctx.context,
                                affected_items=[listing_id],
                                impact_description="Some listing information may be missing",
                            )

                        # Check for status-related warnings
                        status = details.get("status", "unknown")
                        if status in ["sold", "deleted"]:
                            warning_manager.add_warning(
                                f"Listing {listing_id} has status: {status}",
                                ErrorSeverity.LOW,
                                error_ctx.context,
                                affected_items=[listing_id],
                                impact_description=f"Listing is no longer available ({status})",
                            )

                        return details

                    finally:
                        if page:
                            await page.close()
                        await browser_manager.release_context(context)

                # Execute with concurrency control
                details = await browser_manager.execute_with_semaphore(
                    fetch_operation()
                )

                # Create successful page metric with warning information
                page_metric = PageMetrics(
                    page_number=1,
                    url=url,
                    start_time=start_time,
                    end_time=time.time(),
                    success=True,
                    retry_count=attempt,
                    error_message=None,
                    results_count=1,
                    warning_count=len(warning_manager.get_warnings()),
                )
                tracker.add_page_metric(page_metric)

                # Get browser performance metrics
                browser_metrics = browser_manager.get_performance_metrics()
                tracker.set_browser_contexts_used(
                    browser_metrics["contexts_in_use"]
                    + browser_metrics["contexts_in_pool"]
                )
                tracker.set_concurrent_level(1)  # Single listing request

                # Generate final metrics
                request_metrics = tracker.get_request_metrics()

                # Log successful operation
                if attempt > 0:
                    logger.log_operation_summary(
                        operation=f"fetch_details_{listing_id}",
                        total_items=1,
                        successful_items=1,
                        warnings=warning_manager.get_warnings(),
                        errors=[],
                        duration=request_metrics.total_time,
                    )

                # Prepare response with comprehensive information
                response = {
                    "success": True,
                    "data": details,
                    "time_taken": round(request_metrics.total_time, 3),
                    "performance_metrics": request_metrics.to_dict(),
                    "browser_metrics": browser_metrics,
                }

                # Add warning information if present
                warnings = warning_manager.get_warnings()
                if warnings:
                    response["warnings"] = warning_manager.get_user_friendly_messages()
                    response["detailed_warnings"] = [w.to_dict() for w in warnings]
                    response["warning_summary"] = warning_manager.get_warning_summary()

                return response

            except Exception as e:
                # Classify and handle the error
                error_ctx.context.retry_attempt = attempt
                structured_error = error_ctx.handle_exception(e, "detail_fetch")
                last_structured_error = structured_error

                # Check if we should retry based on error classification
                if attempt < retry_count and structured_error.should_retry(retry_count):
                    # Add warning about retry attempt
                    warning_manager.add_warning(
                        f"Retrying listing {listing_id} after {structured_error.category.value} error (attempt {attempt + 1}/{retry_count + 1})",
                        ErrorSeverity.MEDIUM,
                        error_ctx.context,
                        affected_items=[listing_id],
                        impact_description=f"Temporary delay before retry due to {structured_error.category.value} error",
                    )

                    # Exponential backoff with jitter
                    import asyncio
                    import random

                    wait_time = (2**attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                    continue

                # All retries exhausted or non-recoverable error
                error_msg = (
                    f"Failed after {attempt + 1} attempts: {structured_error.message}"
                )

                # Create failed page metric with enhanced information
                page_metric = PageMetrics(
                    page_number=1,
                    url=url,
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    retry_count=attempt,
                    error_message=error_msg,
                    results_count=0,
                    error_category=structured_error.category.value,
                    warning_count=len(warning_manager.get_warnings()),
                )
                tracker.add_page_metric(page_metric)

                # Try to get partial metrics if available
                try:
                    browser_metrics = browser_manager.get_performance_metrics()
                    tracker.set_browser_contexts_used(
                        browser_metrics["contexts_in_use"]
                        + browser_metrics["contexts_in_pool"]
                    )
                    tracker.set_concurrent_level(1)

                    request_metrics = tracker.get_request_metrics()

                    # Log failed operation
                    logger.log_operation_summary(
                        operation=f"fetch_details_{listing_id}",
                        total_items=1,
                        successful_items=0,
                        warnings=warning_manager.get_warnings(),
                        errors=[structured_error],
                        duration=request_metrics.total_time,
                    )

                    # Prepare comprehensive error response
                    response = {
                        "success": False,
                        "error": structured_error.message,
                        "error_category": structured_error.category.value,
                        "error_severity": structured_error.severity.value,
                        "recovery_suggestions": structured_error.recovery_suggestions,
                        "data": None,
                        "time_taken": round(request_metrics.total_time, 3),
                        "performance_metrics": request_metrics.to_dict(),
                        "browser_metrics": browser_metrics,
                    }

                    # Add warning information if present
                    warnings = warning_manager.get_warnings()
                    if warnings:
                        response["warnings"] = (
                            warning_manager.get_user_friendly_messages()
                        )
                        response["detailed_warnings"] = [w.to_dict() for w in warnings]

                    return response

                except Exception as e:
                    # Fallback response if metrics collection also fails
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": structured_error.message,
                            "category": structured_error.category.value,
                            "severity": structured_error.severity.value,
                            "recovery_suggestions": structured_error.recovery_suggestions,
                        },
                    ) from e

        # This should never be reached, but just in case
        if last_structured_error:
            error_msg = f"Final error: {last_structured_error.message}"
            raise HTTPException(
                status_code=500,
                detail={
                    "error": error_msg,
                    "category": last_structured_error.category.value,
                    "severity": last_structured_error.severity.value,
                    "recovery_suggestions": last_structured_error.recovery_suggestions,
                },
            )
        else:
            raise HTTPException(
                status_code=500, detail="Unexpected error in retry loop"
            )
