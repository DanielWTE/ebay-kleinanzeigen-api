import asyncio
import time
import random
from urllib.parse import urlencode

from fastapi import HTTPException

from utils.browser import PlaywrightManager, OptimizedPlaywrightManager
from utils.performance import PageMetrics, track_page_performance
from utils.error_handling import (
    ErrorClassifier,
    WarningManager,
    ErrorLogger,
    ErrorContext,
    ErrorSeverity,
    error_handling_context,
)


async def get_ads(page):
    try:
        items = await page.query_selector_all(
            ".ad-listitem:not(.is-topad):not(.badge-hint-pro-small-srp)"
        )
        results = []
        for item in items:
            article = await item.query_selector("article")
            if article:
                data_adid = await article.get_attribute("data-adid")
                data_href = await article.get_attribute("data-href")
                # Get title from h2 element
                title_element = await article.query_selector(
                    "h2.text-module-begin a.ellipsis"
                )
                title_text = await title_element.inner_text() if title_element else ""
                # Get price and description
                price = await article.query_selector(
                    "p.aditem-main--middle--price-shipping--price"
                )
                # strip € and VB and strip whitespace
                price_text = await price.inner_text() if price else ""
                price_text = (
                    price_text.replace("€", "")
                    .replace("VB", "")
                    .replace(".", "")
                    .strip()
                )
                description = await article.query_selector(
                    "p.aditem-main--middle--description"
                )
                description_text = await description.inner_text() if description else ""
                if data_adid and data_href:
                    data_href = f"https://www.kleinanzeigen.de{data_href}"
                    results.append(
                        {
                            "adid": data_adid,
                            "url": data_href,
                            "title": title_text,
                            "price": price_text,
                            "description": description_text,
                        }
                    )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_page(browser_manager: PlaywrightManager, url: str):
    page = await browser_manager.new_context_page()
    try:
        await page.goto(url, timeout=120000)
        await page.wait_for_load_state("networkidle")
        return await get_ads(page)
    finally:
        await browser_manager.close_page(page)


async def optimized_fetch_page(
    browser_manager: OptimizedPlaywrightManager,
    url: str,
    page_num: int,
    retry_count: int = 2,
    logger: ErrorLogger = None,
) -> tuple[list, PageMetrics]:
    """
    Optimized page fetching with comprehensive error handling and performance tracking.

    Args:
        browser_manager: OptimizedPlaywrightManager instance
        url: URL to fetch
        page_num: Page number for tracking
        retry_count: Maximum number of retries (default: 2)
        logger: Optional error logger instance

    Returns:
        Tuple of (results_list, PageMetrics)
    """
    if logger is None:
        logger = ErrorLogger()

    with error_handling_context(
        operation="fetch_page", page_number=page_num, url=url, logger=logger
    ) as error_ctx:
        async with track_page_performance(page_num, url) as tracker:
            last_structured_error = None

            for attempt in range(retry_count + 1):  # +1 for initial attempt
                try:
                    # Use semaphore-controlled execution
                    async def fetch_operation():
                        context = await browser_manager.get_context()
                        page = None
                        try:
                            page = await context.new_page()

                            # Navigate to page with timeout
                            await page.goto(url, timeout=120000)
                            await page.wait_for_load_state("networkidle")

                            # Extract ads from page
                            results = await get_ads(page)
                            tracker.set_results_count(len(results))

                            # Add success metrics to error context
                            if len(results) == 0:
                                error_ctx.add_warning(
                                    f"No results found on page {page_num}",
                                    ErrorSeverity.LOW,
                                    affected_items=[f"page_{page_num}"],
                                    impact_description="Empty page may indicate end of results or filtering issues",
                                )

                            return results

                        finally:
                            if page:
                                await page.close()
                            await browser_manager.release_context(context)

                    # Execute with concurrency control
                    results = await browser_manager.execute_with_semaphore(
                        fetch_operation()
                    )
                    tracker.set_retry_count(attempt)

                    # Create enhanced metrics with error categorization
                    metrics = tracker.get_metrics()
                    if error_ctx.has_warnings():
                        metrics.warning_count = len(error_ctx.warnings.get_warnings())

                    return results, metrics

                except Exception as e:
                    # Classify and handle the error
                    error_ctx.context.retry_attempt = attempt
                    structured_error = error_ctx.handle_exception(e, "page_fetch")
                    last_structured_error = structured_error

                    tracker.set_retry_count(attempt)

                    # Check if we should retry based on error classification
                    if attempt < retry_count and structured_error.should_retry(
                        retry_count
                    ):
                        # Exponential backoff with jitter
                        wait_time = (2**attempt) + random.uniform(0, 1)

                        # Add warning about retry attempt
                        error_ctx.add_warning(
                            f"Retrying page {page_num} after {structured_error.category.value} error (attempt {attempt + 1}/{retry_count + 1})",
                            ErrorSeverity.MEDIUM,
                            affected_items=[f"page_{page_num}"],
                            impact_description=f"Temporary delay of {wait_time:.1f}s before retry",
                        )

                        await asyncio.sleep(wait_time)
                        continue

                    # All retries exhausted or non-recoverable error
                    error_msg = f"Failed after {attempt + 1} attempts: {structured_error.message}"
                    tracker.set_error(error_msg)

                    # Create enhanced metrics with error information
                    metrics = tracker.get_metrics()
                    metrics.error_category = structured_error.category.value
                    metrics.warning_count = len(error_ctx.warnings.get_warnings())

                    return [], metrics

            # This should never be reached, but just in case
            fallback_error = "Unexpected error in retry loop"
            if last_structured_error:
                fallback_error = f"Final error: {last_structured_error.message}"

            tracker.set_error(fallback_error)
            metrics = tracker.get_metrics()
            if last_structured_error:
                metrics.error_category = last_structured_error.category.value
            metrics.warning_count = len(error_ctx.warnings.get_warnings())

            return [], metrics


async def get_inserate_klaz(
    browser_manager: PlaywrightManager,
    query: str = None,
    location: str = None,
    radius: int = None,
    min_price: int = None,
    max_price: int = None,
    page_count: int = 1,
):
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
        params["keywords"] = query
    if location:
        params["locationStr"] = location
    if radius:
        params["radius"] = radius

    # Construct the full URL and get it
    search_url = base_url + search_path + ("?" + urlencode(params) if params else "")

    tasks = []
    for i in range(1, page_count + 1):
        url = search_url.format(page=i)
        tasks.append(fetch_page(browser_manager, url))

    try:
        results_from_pages = await asyncio.gather(*tasks)
        # Flatten the list of lists into a single list
        all_results = [item for sublist in results_from_pages for item in sublist]
        return all_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_inserate_klaz_optimized(
    browser_manager: OptimizedPlaywrightManager,
    query: str = None,
    location: str = None,
    radius: int = None,
    min_price: int = None,
    max_price: int = None,
    page_count: int = 1,
) -> dict:
    """
    Optimized version of get_inserate_klaz with comprehensive error handling and detailed metrics.

    Args:
        browser_manager: OptimizedPlaywrightManager instance
        query: Search query string
        location: Location filter
        radius: Search radius
        min_price: Minimum price filter
        max_price: Maximum price filter
        page_count: Number of pages to fetch

    Returns:
        Dictionary containing results, performance metrics, and comprehensive warnings
    """
    from utils.performance import PerformanceTracker

    # Initialize error handling and performance tracking
    logger = ErrorLogger("inserate_scraper")
    warning_manager = WarningManager()
    tracker = PerformanceTracker()
    tracker.start_request()

    with error_handling_context(
        operation="multi_page_scrape", logger=logger
    ) as error_ctx:
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
            params["keywords"] = query
        if location:
            params["locationStr"] = location
        if radius:
            params["radius"] = radius

        # Construct the full URL and get it
        search_url = (
            base_url + search_path + ("?" + urlencode(params) if params else "")
        )

        # Create tasks for concurrent processing
        tasks = []
        for i in range(1, page_count + 1):
            url = search_url.format(page=i)
            tasks.append(optimized_fetch_page(browser_manager, url, i, logger=logger))

        # Set concurrent level for metrics
        tracker.set_concurrent_level(min(page_count, browser_manager._semaphore._value))

        try:
            # Execute all tasks concurrently with controlled concurrency
            results_and_metrics = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and collect comprehensive metrics
            all_results = []
            successful_pages = 0
            failed_pages = 0
            total_warnings = 0

            for i, result in enumerate(results_and_metrics):
                if isinstance(result, Exception):
                    # Handle exceptions that weren't caught by optimized_fetch_page
                    failed_pages += 1

                    # Classify the exception
                    error_context = ErrorContext(
                        operation="page_fetch_gather",
                        page_number=i + 1,
                        url=search_url.format(page=i + 1),
                    )
                    structured_error = ErrorClassifier.classify_exception(
                        result, error_context, "concurrent_page_fetch"
                    )

                    # Add to warning manager
                    warning_manager.add_error_as_warning(
                        structured_error,
                        affected_items=[f"page_{i + 1}"],
                        impact_description=f"Page {i + 1} results unavailable due to {structured_error.category.value} error",
                    )

                    # Log the error
                    logger.log_error(structured_error)

                    # Create a failed page metric with enhanced information
                    failed_metric = PageMetrics(
                        page_number=i + 1,
                        url=search_url.format(page=i + 1),
                        start_time=time.time(),
                        end_time=time.time(),
                        success=False,
                        retry_count=0,
                        error_message=structured_error.message,
                        results_count=0,
                        error_category=structured_error.category.value,
                    )
                    tracker.add_page_metric(failed_metric)
                else:
                    # Unpack results and metrics
                    page_results, page_metrics = result
                    tracker.add_page_metric(page_metrics)

                    if page_metrics.success:
                        all_results.extend(page_results)
                        successful_pages += 1

                        # Check for potential issues even in successful pages
                        if page_metrics.retry_count > 0:
                            warning_manager.add_warning(
                                f"Page {page_metrics.page_number} succeeded after {page_metrics.retry_count} retries",
                                ErrorSeverity.LOW,
                                error_ctx.context,
                                affected_items=[f"page_{page_metrics.page_number}"],
                                impact_description="Temporary network or server issues resolved",
                            )

                        if page_metrics.results_count == 0:
                            warning_manager.add_warning(
                                f"Page {page_metrics.page_number} returned no results",
                                ErrorSeverity.LOW,
                                error_ctx.context,
                                affected_items=[f"page_{page_metrics.page_number}"],
                                impact_description="May indicate end of available results or overly restrictive filters",
                            )
                    else:
                        failed_pages += 1
                        warning_manager.add_warning(
                            f"Page {page_metrics.page_number} failed: {page_metrics.error_message}",
                            ErrorSeverity.MEDIUM
                            if page_metrics.error_category == "recoverable"
                            else ErrorSeverity.HIGH,
                            error_ctx.context,
                            affected_items=[f"page_{page_metrics.page_number}"],
                            impact_description=f"Results from page {page_metrics.page_number} unavailable",
                        )

                    # Count warnings from individual page processing
                    total_warnings += page_metrics.warning_count

            # Get browser performance metrics
            browser_metrics = browser_manager.get_performance_metrics()
            tracker.set_browser_contexts_used(
                browser_metrics["contexts_in_use"] + browser_metrics["contexts_in_pool"]
            )

            # Generate final metrics
            request_metrics = tracker.get_request_metrics()

            # Add operation-level warnings based on overall performance
            success_rate = (
                (successful_pages / page_count) * 100 if page_count > 0 else 0
            )

            if success_rate < 50:
                warning_manager.add_warning(
                    f"Low success rate: Only {successful_pages}/{page_count} pages succeeded ({success_rate:.1f}%)",
                    ErrorSeverity.HIGH,
                    error_ctx.context,
                    affected_items=[f"pages_1_to_{page_count}"],
                    impact_description="Significant data loss due to multiple page failures",
                )
            elif success_rate < 80:
                warning_manager.add_warning(
                    f"Moderate success rate: {successful_pages}/{page_count} pages succeeded ({success_rate:.1f}%)",
                    ErrorSeverity.MEDIUM,
                    error_ctx.context,
                    affected_items=[f"pages_1_to_{page_count}"],
                    impact_description="Some data loss due to page failures",
                )

            if request_metrics.total_time > 10.0:
                warning_manager.add_warning(
                    f"Slow operation: {request_metrics.total_time:.1f}s for {page_count} pages",
                    ErrorSeverity.MEDIUM,
                    error_ctx.context,
                    impact_description="Performance below optimal levels",
                )

            # Log operation summary
            logger.log_operation_summary(
                operation=f"scrape_{page_count}_pages",
                total_items=page_count,
                successful_items=successful_pages,
                warnings=warning_manager.get_warnings(),
                errors=error_ctx.errors,
                duration=request_metrics.total_time,
            )

            # Prepare comprehensive response
            response = {
                "success": True,
                "results": all_results,
                "unique_results": len(all_results),
                "time_taken": round(request_metrics.total_time, 3),
                "performance_metrics": {
                    **request_metrics.to_dict(),
                    "success_rate": round(success_rate, 2),
                    "pages_failed": failed_pages,
                    "total_warnings": len(warning_manager.get_warnings()),
                },
                "browser_metrics": browser_metrics,
            }

            # Add comprehensive warning information
            warnings = warning_manager.get_warnings()
            if warnings:
                response["warnings"] = warning_manager.get_user_friendly_messages()
                response["detailed_warnings"] = [w.to_dict() for w in warnings]
                response["warning_summary"] = warning_manager.get_warning_summary()
                response["partial_success"] = True

                # Indicate if there are critical issues
                if warning_manager.has_critical_warnings():
                    response["has_critical_warnings"] = True

            return response

        except Exception as e:
            # Handle unexpected critical errors
            structured_error = error_ctx.handle_exception(e, "multi_page_scrape")

            # Try to get partial metrics if available
            try:
                request_metrics = tracker.get_request_metrics()
                browser_metrics = browser_manager.get_performance_metrics()

                return {
                    "success": False,
                    "error": structured_error.message,
                    "error_category": structured_error.category.value,
                    "error_severity": structured_error.severity.value,
                    "recovery_suggestions": structured_error.recovery_suggestions,
                    "results": [],
                    "unique_results": 0,
                    "time_taken": round(request_metrics.total_time, 3),
                    "performance_metrics": request_metrics.to_dict(),
                    "browser_metrics": browser_metrics,
                    "warnings": warning_manager.get_user_friendly_messages()
                    if warning_manager.get_warnings()
                    else [],
                }
            except Exception as e:
                print(e)
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
