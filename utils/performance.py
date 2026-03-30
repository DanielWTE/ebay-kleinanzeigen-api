"""
Performance metrics system for tracking API and scraping performance.

This module provides structured data classes and utilities for measuring
timing, success rates, and resource usage across the application.
"""

import time
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager


@dataclass
class PageMetrics:
    """Metrics for individual page processing operations."""

    page_number: int
    url: str
    start_time: float
    end_time: float
    success: bool
    retry_count: int
    error_message: Optional[str] = None
    results_count: int = 0
    error_category: Optional[str] = None  # Added for error categorization
    warning_count: int = 0  # Added for warning tracking

    @property
    def duration(self) -> float:
        """Calculate the duration of the page processing."""
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "page_number": self.page_number,
            "time_taken": round(self.duration, 3),
            "success": self.success,
            "retry_count": self.retry_count,
            "results_count": self.results_count,
            "error": self.error_message,
        }

        # Add error categorization if available
        if self.error_category:
            result["error_category"] = self.error_category

        # Add warning information if present
        if self.warning_count > 0:
            result["warning_count"] = self.warning_count

        return result


@dataclass
class RequestMetrics:
    """Comprehensive metrics for entire request operations."""

    total_time: float
    pages_requested: int
    pages_successful: int
    pages_failed: int
    concurrent_level: int
    browser_contexts_used: int
    page_metrics: List[PageMetrics] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.pages_requested == 0:
            return 0.0
        return (self.pages_successful / self.pages_requested) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        page_times = [pm.duration for pm in self.page_metrics if pm.success]

        return {
            "pages_requested": self.pages_requested,
            "pages_successful": self.pages_successful,
            "pages_failed": self.pages_failed,
            "concurrent_level": self.concurrent_level,
            "browser_contexts_used": self.browser_contexts_used,
            "success_rate": round(self.success_rate, 2),
            "average_page_time": round(statistics.mean(page_times), 3)
            if page_times
            else 0.0,
            "slowest_page_time": round(max(page_times), 3) if page_times else 0.0,
            "fastest_page_time": round(min(page_times), 3) if page_times else 0.0,
            "page_details": [pm.to_dict() for pm in self.page_metrics],
        }


class PerformanceTracker:
    """Utility class for tracking performance metrics during operations."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.page_metrics: List[PageMetrics] = []
        self.concurrent_level: int = 0
        self.browser_contexts_used: int = 0

    def start_request(self) -> None:
        """Mark the start of a request operation."""
        self.start_time = time.time()
        self.page_metrics.clear()

    def add_page_metric(self, page_metric: PageMetrics) -> None:
        """Add a page metric to the tracker."""
        self.page_metrics.append(page_metric)

    def set_concurrent_level(self, level: int) -> None:
        """Set the concurrent processing level achieved."""
        self.concurrent_level = level

    def set_browser_contexts_used(self, count: int) -> None:
        """Set the number of browser contexts used."""
        self.browser_contexts_used = count

    def get_request_metrics(self) -> RequestMetrics:
        """Generate comprehensive request metrics."""
        if self.start_time is None:
            raise ValueError("Request tracking not started")

        total_time = time.time() - self.start_time
        pages_successful = sum(1 for pm in self.page_metrics if pm.success)
        pages_failed = len(self.page_metrics) - pages_successful

        return RequestMetrics(
            total_time=total_time,
            pages_requested=len(self.page_metrics),
            pages_successful=pages_successful,
            pages_failed=pages_failed,
            concurrent_level=self.concurrent_level,
            browser_contexts_used=self.browser_contexts_used,
            page_metrics=self.page_metrics.copy(),
        )


@asynccontextmanager
async def track_page_performance(page_number: int, url: str):
    """
    Context manager for tracking individual page performance.

    Usage:
        async with track_page_performance(1, "https://example.com") as tracker:
            # Perform page operations
            tracker.set_results_count(10)
            tracker.set_retry_count(1)
    """

    class PageTracker:
        def __init__(self, page_num: int, page_url: str):
            self.page_number = page_num
            self.url = page_url
            self.start_time = time.time()
            self.results_count = 0
            self.retry_count = 0
            self.error_message: Optional[str] = None
            self.success = True

        def set_results_count(self, count: int):
            self.results_count = count

        def set_retry_count(self, count: int):
            self.retry_count = count

        def set_error(self, error: str):
            self.error_message = error
            self.success = False

        def get_metrics(self) -> PageMetrics:
            return PageMetrics(
                page_number=self.page_number,
                url=self.url,
                start_time=self.start_time,
                end_time=time.time(),
                success=self.success,
                retry_count=self.retry_count,
                error_message=self.error_message,
                results_count=self.results_count,
            )

    tracker = PageTracker(page_number, url)
    try:
        yield tracker
    except Exception as e:
        tracker.set_error(str(e))
        raise
    finally:
        # Metrics are captured when get_metrics() is called
        pass


class MetricsAggregator:
    """Utility class for aggregating and analyzing performance metrics."""

    @staticmethod
    def calculate_percentiles(
        values: List[float], percentiles: List[int] = None
    ) -> Dict[str, float]:
        """
        Calculate percentiles for a list of values.

        Args:
            values: List of numeric values
            percentiles: List of percentile values to calculate (default: [50, 90, 95, 99])

        Returns:
            Dictionary mapping percentile names to values
        """
        if not values:
            return {}

        if percentiles is None:
            percentiles = [50, 90, 95, 99]

        sorted_values = sorted(values)
        result = {}

        for p in percentiles:
            if p < 0 or p > 100:
                continue

            if p == 0:
                result[f"p{p}"] = sorted_values[0]
            elif p == 100:
                result[f"p{p}"] = sorted_values[-1]
            else:
                # Use the nearest-rank method
                n = len(sorted_values)
                rank = (p / 100) * (n - 1)
                lower_index = int(rank)
                upper_index = min(lower_index + 1, n - 1)

                if lower_index == upper_index:
                    result[f"p{p}"] = sorted_values[lower_index]
                else:
                    # Linear interpolation
                    weight = rank - lower_index
                    result[f"p{p}"] = (
                        sorted_values[lower_index] * (1 - weight)
                        + sorted_values[upper_index] * weight
                    )

        return {k: round(v, 3) for k, v in result.items()}

    @staticmethod
    def analyze_request_metrics(metrics_list: List[RequestMetrics]) -> Dict[str, Any]:
        """
        Analyze multiple request metrics to provide aggregate insights.

        Args:
            metrics_list: List of RequestMetrics objects

        Returns:
            Dictionary containing aggregate analysis
        """
        if not metrics_list:
            return {}

        # Extract timing data
        total_times = [m.total_time for m in metrics_list]
        success_rates = [m.success_rate for m in metrics_list]

        # Extract page timing data from all requests
        all_page_times = []
        for metrics in metrics_list:
            all_page_times.extend(
                [pm.duration for pm in metrics.page_metrics if pm.success]
            )

        # Calculate aggregate statistics
        analysis = {
            "total_requests": len(metrics_list),
            "request_times": {
                "average": round(statistics.mean(total_times), 3),
                "median": round(statistics.median(total_times), 3),
                "min": round(min(total_times), 3),
                "max": round(max(total_times), 3),
                "std_dev": round(
                    statistics.stdev(total_times) if len(total_times) > 1 else 0, 3
                ),
            },
            "success_rates": {
                "average": round(statistics.mean(success_rates), 2),
                "min": round(min(success_rates), 2),
                "max": round(max(success_rates), 2),
            },
            "page_processing": {
                "total_pages": sum(m.pages_requested for m in metrics_list),
                "successful_pages": sum(m.pages_successful for m in metrics_list),
                "failed_pages": sum(m.pages_failed for m in metrics_list),
            },
        }

        # Add percentile analysis for request times
        analysis["request_time_percentiles"] = MetricsAggregator.calculate_percentiles(
            total_times
        )

        # Add percentile analysis for page times if available
        if all_page_times:
            analysis["page_time_percentiles"] = MetricsAggregator.calculate_percentiles(
                all_page_times
            )
            analysis["page_processing"]["average_time"] = round(
                statistics.mean(all_page_times), 3
            )

        return analysis

    @staticmethod
    def generate_performance_summary(request_metrics: RequestMetrics) -> Dict[str, Any]:
        """
        Generate a human-readable performance summary for a single request.

        Args:
            request_metrics: RequestMetrics object to summarize

        Returns:
            Dictionary containing performance summary
        """
        page_times = [pm.duration for pm in request_metrics.page_metrics if pm.success]

        summary = {
            "overall_performance": "excellent"
            if request_metrics.total_time < 3.0
            else "good"
            if request_metrics.total_time < 5.0
            else "needs_improvement",
            "total_duration": f"{request_metrics.total_time:.2f}s",
            "pages_processed": f"{request_metrics.pages_successful}/{request_metrics.pages_requested}",
            "success_rate": f"{request_metrics.success_rate:.1f}%",
            "concurrency_achieved": request_metrics.concurrent_level,
            "browser_efficiency": f"{request_metrics.browser_contexts_used} contexts used",
        }

        if page_times:
            summary["page_timing"] = {
                "fastest": f"{min(page_times):.2f}s",
                "slowest": f"{max(page_times):.2f}s",
                "average": f"{statistics.mean(page_times):.2f}s",
            }

        # Add warnings for performance issues
        warnings = []
        if request_metrics.success_rate < 95:
            warnings.append(f"Low success rate: {request_metrics.success_rate:.1f}%")
        if request_metrics.total_time > 5.0:
            warnings.append(f"Slow response time: {request_metrics.total_time:.2f}s")
        if request_metrics.pages_failed > 0:
            warnings.append(f"{request_metrics.pages_failed} pages failed to process")

        if warnings:
            summary["warnings"] = warnings

        return summary
