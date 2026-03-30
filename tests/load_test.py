"""
Load Testing Framework for Kleinanzeigen API Performance Optimization

This module provides comprehensive load testing capabilities to validate API performance
under concurrent load conditions. It simulates multiple concurrent users making API
requests and measures response times, success rates, and error conditions.

Features:
- Multiple test scenarios (single user, multiple users, stress test)
- Concurrent user simulation with realistic request patterns
- Comprehensive performance measurement and reporting
- Detailed error analysis and categorization
- Recommendations based on performance test results
"""

import asyncio
import aiohttp
import time
import statistics
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TestScenario(Enum):
    """Test scenario types for different load testing patterns"""

    SINGLE_USER_MULTIPLE_PAGES = "single_user_multiple_pages"
    MULTIPLE_USERS_STANDARD_LOAD = "multiple_users_standard_load"
    STRESS_TEST = "stress_test"
    MIXED_WORKLOAD = "mixed_workload"


@dataclass
class RequestResult:
    """Individual request result with comprehensive metrics"""

    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_size: int = 0
    user_id: int = 0
    timestamp: float = 0
    request_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.request_params is None:
            self.request_params = {}


@dataclass
class UserMetrics:
    """Performance metrics for a single simulated user"""

    user_id: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    total_time: float
    requests_per_second: float
    error_rate: float
    request_results: List[RequestResult]


@dataclass
class LoadTestReport:
    """Comprehensive load test report with performance analysis"""

    scenario: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    overall_success_rate: float
    overall_error_rate: float

    # Response time statistics
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float

    # Throughput metrics
    requests_per_second: float
    concurrent_users: int

    # Per-user metrics
    user_metrics: List[UserMetrics]

    # Error analysis
    error_breakdown: Dict[str, int]
    status_code_breakdown: Dict[int, int]

    # Performance recommendations
    recommendations: List[str]

    # Raw data for detailed analysis
    all_request_results: List[RequestResult]


class LoadTester:
    """
    Comprehensive load testing framework for API performance validation.

    This class simulates multiple concurrent users making API requests to validate
    the performance optimizations under realistic load conditions. It provides
    detailed performance measurement, error analysis, and recommendations.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the load tester.

        Args:
            base_url: Base URL of the API to test
        """
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

        # Test configuration
        self.default_timeout = aiohttp.ClientTimeout(total=30)
        self.connector_limit = 100  # Maximum concurrent connections

        # Sample query patterns for realistic testing
        self.sample_queries = [
            {"query": "laptop", "location": "Berlin", "page_count": 5},
            {"query": "smartphone", "location": "München", "page_count": 3},
            {"query": "fahrrad", "location": "Hamburg", "page_count": 10},
            {"query": "auto", "location": "Köln", "page_count": 2},
            {"query": "möbel", "location": "Frankfurt", "page_count": 7},
            {"query": "elektronik", "location": "Stuttgart", "page_count": 4},
            {"query": "kleidung", "location": "Düsseldorf", "page_count": 6},
            {"query": "bücher", "location": "Leipzig", "page_count": 8},
        ]

        # Sample listing IDs for detail endpoint testing
        self.sample_listing_ids = [
            "2123456789",
            "2234567890",
            "2345678901",
            "2456789012",
            "2567890123",
            "2678901234",
            "2789012345",
            "2890123456",
        ]

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Initialize HTTP session with optimized settings"""
        connector = aiohttp.TCPConnector(
            limit=self.connector_limit,
            limit_per_host=50,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.default_timeout,
            headers={
                "User-Agent": "LoadTester/1.0 (Performance Testing)",
                "Accept": "application/json",
                "Connection": "keep-alive",
            },
        )

    async def close_session(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    def get_random_query_params(self) -> Dict[str, Any]:
        """Generate random query parameters for realistic testing"""
        base_params = random.choice(self.sample_queries).copy()

        # Add random price filters occasionally
        if random.random() < 0.3:
            base_params["min_price"] = random.choice([10, 50, 100, 200])

        if random.random() < 0.3:
            base_params["max_price"] = random.choice([500, 1000, 2000, 5000])

        # Add random radius occasionally
        if random.random() < 0.4:
            base_params["radius"] = random.choice([5, 10, 25, 50])

        return base_params

    def get_random_listing_id(self) -> str:
        """Get a random listing ID for detail endpoint testing"""
        return random.choice(self.sample_listing_ids)

    async def make_request(
        self, endpoint: str, params: Dict[str, Any] = None, user_id: int = 0
    ) -> RequestResult:
        """
        Make a single API request with comprehensive error handling and metrics.

        Args:
            endpoint: API endpoint to test
            params: Query parameters
            user_id: ID of the simulated user making the request

        Returns:
            RequestResult with detailed metrics and error information
        """
        if not self.session:
            await self.start_session()

        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            async with self.session.get(url, params=params) as response:
                response_text = await response.text()
                end_time = time.time()
                response_time = end_time - start_time

                # Determine success based on status code and response content
                success = 200 <= response.status < 300
                error_message = None

                if not success:
                    error_message = f"HTTP {response.status}: {response.reason}"
                    try:
                        # Try to extract error details from JSON response
                        response_data = json.loads(response_text)
                        if (
                            isinstance(response_data, dict)
                            and "detail" in response_data
                        ):
                            error_message = (
                                f"HTTP {response.status}: {response_data['detail']}"
                            )
                    except json.JSONDecodeError:
                        pass

                return RequestResult(
                    endpoint=endpoint,
                    method="GET",
                    status_code=response.status,
                    response_time=response_time,
                    success=success,
                    error_message=error_message,
                    response_size=len(response_text),
                    user_id=user_id,
                    timestamp=start_time,
                    request_params=params or {},
                )

        except asyncio.TimeoutError:
            end_time = time.time()
            return RequestResult(
                endpoint=endpoint,
                method="GET",
                status_code=0,
                response_time=end_time - start_time,
                success=False,
                error_message="Request timeout",
                user_id=user_id,
                timestamp=start_time,
                request_params=params or {},
            )

        except Exception as e:
            end_time = time.time()
            return RequestResult(
                endpoint=endpoint,
                method="GET",
                status_code=0,
                response_time=end_time - start_time,
                success=False,
                error_message=f"Connection error: {str(e)}",
                user_id=user_id,
                timestamp=start_time,
                request_params=params or {},
            )

    async def simulate_single_user(
        self,
        user_id: int,
        requests_per_user: int,
        scenario: TestScenario,
        delay_between_requests: float = 0.1,
    ) -> UserMetrics:
        """
        Simulate a single user making multiple requests.

        Args:
            user_id: Unique identifier for the user
            requests_per_user: Number of requests this user should make
            scenario: Test scenario type to determine request patterns
            delay_between_requests: Delay between requests in seconds

        Returns:
            UserMetrics with comprehensive performance data for this user
        """
        user_start_time = time.time()
        request_results = []

        for request_num in range(requests_per_user):
            # Determine endpoint and parameters based on scenario
            if scenario == TestScenario.SINGLE_USER_MULTIPLE_PAGES:
                # Focus on /inserate endpoint with varying page counts
                endpoint = "/inserate"
                params = self.get_random_query_params()
                params["page_count"] = random.randint(1, 20)

            elif scenario == TestScenario.MULTIPLE_USERS_STANDARD_LOAD:
                # Mix of endpoints with standard parameters
                endpoint_choice = random.choices(
                    ["/inserate", "/inserat/{id}", "/inserate-detailed"],
                    weights=[0.5, 0.3, 0.2],
                )[0]

                if endpoint_choice == "/inserat/{id}":
                    endpoint = f"/inserat/{self.get_random_listing_id()}"
                    params = {}
                elif endpoint_choice == "/inserate-detailed":
                    endpoint = "/inserate-detailed"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(1, 5)
                    params["max_concurrent_details"] = random.randint(3, 8)
                else:
                    endpoint = "/inserate"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(1, 10)

            elif scenario == TestScenario.STRESS_TEST:
                # High-load patterns with larger page counts
                endpoint_choice = random.choices(
                    ["/inserate", "/inserate-detailed"], weights=[0.6, 0.4]
                )[0]

                if endpoint_choice == "/inserate-detailed":
                    endpoint = "/inserate-detailed"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(10, 20)
                    params["max_concurrent_details"] = random.randint(5, 10)
                else:
                    endpoint = "/inserate"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(15, 20)

            else:  # MIXED_WORKLOAD
                # Realistic mix of all endpoints
                endpoint_choice = random.choices(
                    ["/inserate", "/inserat/{id}", "/inserate-detailed"],
                    weights=[0.4, 0.4, 0.2],
                )[0]

                if endpoint_choice == "/inserat/{id}":
                    endpoint = f"/inserat/{self.get_random_listing_id()}"
                    params = {}
                elif endpoint_choice == "/inserate-detailed":
                    endpoint = "/inserate-detailed"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(1, 10)
                    params["max_concurrent_details"] = random.randint(3, 7)
                else:
                    endpoint = "/inserate"
                    params = self.get_random_query_params()
                    params["page_count"] = random.randint(1, 15)

            # Make the request
            result = await self.make_request(endpoint, params, user_id)
            request_results.append(result)

            # Add delay between requests to simulate realistic user behavior
            if delay_between_requests > 0 and request_num < requests_per_user - 1:
                await asyncio.sleep(delay_between_requests + random.uniform(0, 0.1))

        # Calculate user metrics
        user_end_time = time.time()
        total_time = user_end_time - user_start_time

        successful_requests = sum(1 for r in request_results if r.success)
        failed_requests = len(request_results) - successful_requests

        response_times = [r.response_time for r in request_results]
        average_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        requests_per_second = len(request_results) / total_time if total_time > 0 else 0
        error_rate = (
            (failed_requests / len(request_results)) * 100 if request_results else 0
        )

        return UserMetrics(
            user_id=user_id,
            total_requests=len(request_results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=average_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            total_time=total_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            request_results=request_results,
        )

    async def simulate_concurrent_users(
        self,
        user_count: int,
        requests_per_user: int,
        scenario: TestScenario = TestScenario.MULTIPLE_USERS_STANDARD_LOAD,
        delay_between_requests: float = 0.1,
    ) -> List[UserMetrics]:
        """
        Simulate multiple concurrent users making API requests.

        This is the core method that implements concurrent user simulation
        as required by the specifications.

        Args:
            user_count: Number of concurrent users to simulate
            requests_per_user: Number of requests each user should make
            scenario: Test scenario type
            delay_between_requests: Delay between requests for each user

        Returns:
            List of UserMetrics for each simulated user
        """
        print(
            f"[INFO] Starting {scenario.value} with {user_count} users, "
            f"{requests_per_user} requests per user"
        )

        # Create tasks for all users
        user_tasks = [
            self.simulate_single_user(
                user_id=i,
                requests_per_user=requests_per_user,
                scenario=scenario,
                delay_between_requests=delay_between_requests,
            )
            for i in range(user_count)
        ]

        # Execute all user simulations concurrently
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)

        # Handle any exceptions that occurred during user simulation
        valid_metrics = []
        for i, metrics in enumerate(user_metrics):
            if isinstance(metrics, Exception):
                print(f"[ERROR] User {i} simulation failed: {metrics}")
                # Create a failed user metrics object
                failed_metrics = UserMetrics(
                    user_id=i,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=requests_per_user,
                    average_response_time=0,
                    min_response_time=0,
                    max_response_time=0,
                    total_time=0,
                    requests_per_second=0,
                    error_rate=100.0,
                    request_results=[],
                )
                valid_metrics.append(failed_metrics)
            else:
                valid_metrics.append(metrics)

        return valid_metrics

    async def run_single_user_multiple_pages_test(
        self, page_counts: List[int] = None, iterations: int = 3
    ) -> LoadTestReport:
        """
        Test scenario: Single user making requests with varying page counts.

        This scenario validates performance with different page count patterns
        to ensure the optimization works across various request sizes.

        Args:
            page_counts: List of page counts to test (default: [1, 5, 10, 15, 20])
            iterations: Number of iterations for each page count

        Returns:
            LoadTestReport with comprehensive results
        """
        if page_counts is None:
            page_counts = [1, 5, 10, 15, 20]

        print(
            f"[INFO] Running single user multiple pages test: {page_counts} pages, {iterations} iterations each"
        )

        start_time = datetime.now()
        all_results = []

        for page_count in page_counts:
            for iteration in range(iterations):
                params = self.get_random_query_params()
                params["page_count"] = page_count

                result = await self.make_request("/inserate", params, user_id=0)
                all_results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.2)

        end_time = datetime.now()

        # Create user metrics
        user_metrics = [
            UserMetrics(
                user_id=0,
                total_requests=len(all_results),
                successful_requests=sum(1 for r in all_results if r.success),
                failed_requests=sum(1 for r in all_results if not r.success),
                average_response_time=statistics.mean(
                    [r.response_time for r in all_results]
                )
                if all_results
                else 0,
                min_response_time=min([r.response_time for r in all_results])
                if all_results
                else 0,
                max_response_time=max([r.response_time for r in all_results])
                if all_results
                else 0,
                total_time=(end_time - start_time).total_seconds(),
                requests_per_second=len(all_results)
                / (end_time - start_time).total_seconds()
                if (end_time - start_time).total_seconds() > 0
                else 0,
                error_rate=(
                    sum(1 for r in all_results if not r.success) / len(all_results)
                )
                * 100
                if all_results
                else 0,
                request_results=all_results,
            )
        ]

        return self._generate_report(
            TestScenario.SINGLE_USER_MULTIPLE_PAGES,
            start_time,
            end_time,
            user_metrics,
            all_results,
        )

    async def run_multiple_users_standard_load_test(
        self, user_count: int = 5, requests_per_user: int = 5
    ) -> LoadTestReport:
        """
        Test scenario: Multiple users with standard load patterns.

        This scenario simulates realistic concurrent usage with multiple users
        making typical API requests simultaneously.

        Args:
            user_count: Number of concurrent users (default: 5)
            requests_per_user: Requests per user (default: 5)

        Returns:
            LoadTestReport with comprehensive results
        """
        print(
            f"[INFO] Running multiple users standard load test: {user_count} users, {requests_per_user} requests each"
        )

        start_time = datetime.now()

        user_metrics = await self.simulate_concurrent_users(
            user_count=user_count,
            requests_per_user=requests_per_user,
            scenario=TestScenario.MULTIPLE_USERS_STANDARD_LOAD,
            delay_between_requests=0.5,  # Realistic delay between user requests
        )

        end_time = datetime.now()

        # Collect all request results
        all_results = []
        for metrics in user_metrics:
            all_results.extend(metrics.request_results)

        return self._generate_report(
            TestScenario.MULTIPLE_USERS_STANDARD_LOAD,
            start_time,
            end_time,
            user_metrics,
            all_results,
        )

    async def run_stress_test(
        self, user_count: int = 10, requests_per_user: int = 10
    ) -> LoadTestReport:
        """
        Test scenario: High-load stress testing.

        This scenario pushes the system to its limits with many concurrent users
        making high-page-count requests to validate performance under stress.

        Args:
            user_count: Number of concurrent users (default: 10)
            requests_per_user: Requests per user (default: 10)

        Returns:
            LoadTestReport with comprehensive results
        """
        print(
            f"[INFO] Running stress test: {user_count} users, {requests_per_user} requests each"
        )

        start_time = datetime.now()

        user_metrics = await self.simulate_concurrent_users(
            user_count=user_count,
            requests_per_user=requests_per_user,
            scenario=TestScenario.STRESS_TEST,
            delay_between_requests=0.1,  # Minimal delay for stress testing
        )

        end_time = datetime.now()

        # Collect all request results
        all_results = []
        for metrics in user_metrics:
            all_results.extend(metrics.request_results)

        return self._generate_report(
            TestScenario.STRESS_TEST, start_time, end_time, user_metrics, all_results
        )

    async def run_mixed_workload_test(
        self, user_count: int = 8, requests_per_user: int = 6
    ) -> LoadTestReport:
        """
        Test scenario: Mixed workload with realistic usage patterns.

        This scenario combines different endpoint usage patterns to simulate
        real-world API usage with a mix of listing searches, detail fetches,
        and combined requests.

        Args:
            user_count: Number of concurrent users (default: 8)
            requests_per_user: Requests per user (default: 6)

        Returns:
            LoadTestReport with comprehensive results
        """
        print(
            f"[INFO] Running mixed workload test: {user_count} users, {requests_per_user} requests each"
        )

        start_time = datetime.now()

        user_metrics = await self.simulate_concurrent_users(
            user_count=user_count,
            requests_per_user=requests_per_user,
            scenario=TestScenario.MIXED_WORKLOAD,
            delay_between_requests=0.3,  # Moderate delay for realistic usage
        )

        end_time = datetime.now()

        # Collect all request results
        all_results = []
        for metrics in user_metrics:
            all_results.extend(metrics.request_results)

        return self._generate_report(
            TestScenario.MIXED_WORKLOAD, start_time, end_time, user_metrics, all_results
        )

    def _generate_report(
        self,
        scenario: TestScenario,
        start_time: datetime,
        end_time: datetime,
        user_metrics: List[UserMetrics],
        all_results: List[RequestResult],
    ) -> LoadTestReport:
        """
        Generate comprehensive load test report with performance analysis.

        Args:
            scenario: Test scenario that was executed
            start_time: Test start time
            end_time: Test end time
            user_metrics: Metrics for each simulated user
            all_results: All individual request results

        Returns:
            LoadTestReport with detailed analysis and recommendations
        """
        total_duration = (end_time - start_time).total_seconds()

        # Calculate overall metrics
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r.success)
        failed_requests = total_requests - successful_requests

        overall_success_rate = (
            (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        )
        overall_error_rate = (
            (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        )

        # Response time statistics
        response_times = [r.response_time for r in all_results if r.success]
        if response_times:
            average_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            p95_response_time = (
                sorted_times[p95_index]
                if p95_index < len(sorted_times)
                else max_response_time
            )
            p99_response_time = (
                sorted_times[p99_index]
                if p99_index < len(sorted_times)
                else max_response_time
            )
        else:
            average_response_time = median_response_time = min_response_time = (
                max_response_time
            ) = 0
            p95_response_time = p99_response_time = 0

        # Throughput metrics
        requests_per_second = (
            total_requests / total_duration if total_duration > 0 else 0
        )
        concurrent_users = len(user_metrics)

        # Error analysis
        error_breakdown = {}
        status_code_breakdown = {}

        for result in all_results:
            # Count status codes
            status_code_breakdown[result.status_code] = (
                status_code_breakdown.get(result.status_code, 0) + 1
            )

            # Count error types
            if not result.success and result.error_message:
                error_type = self._categorize_error(result.error_message)
                error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1

        # Generate recommendations
        recommendations = self._generate_recommendations(
            scenario,
            total_duration,
            overall_success_rate,
            average_response_time,
            p95_response_time,
            requests_per_second,
            error_breakdown,
        )

        return LoadTestReport(
            scenario=scenario.value,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            overall_success_rate=overall_success_rate,
            overall_error_rate=overall_error_rate,
            average_response_time=average_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            requests_per_second=requests_per_second,
            concurrent_users=concurrent_users,
            user_metrics=user_metrics,
            error_breakdown=error_breakdown,
            status_code_breakdown=status_code_breakdown,
            recommendations=recommendations,
            all_request_results=all_results,
        )

    def _categorize_error(self, error_message: str) -> str:
        """Categorize error messages for analysis"""
        error_message_lower = error_message.lower()

        if "timeout" in error_message_lower:
            return "Timeout"
        elif "connection" in error_message_lower:
            return "Connection Error"
        elif "500" in error_message_lower:
            return "Server Error"
        elif "404" in error_message_lower:
            return "Not Found"
        elif "429" in error_message_lower:
            return "Rate Limited"
        elif "400" in error_message_lower:
            return "Bad Request"
        else:
            return "Other"

    def _generate_recommendations(
        self,
        scenario: TestScenario,
        total_duration: float,
        success_rate: float,
        avg_response_time: float,
        p95_response_time: float,
        requests_per_second: float,
        error_breakdown: Dict[str, int],
    ) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []

        # Performance recommendations
        if avg_response_time > 5.0:
            recommendations.append(
                f"High average response time ({avg_response_time:.2f}s). "
                "Consider increasing browser context pool size or reducing concurrent operations."
            )

        if p95_response_time > 10.0:
            recommendations.append(
                f"High P95 response time ({p95_response_time:.2f}s). "
                "Some requests are significantly slower - investigate timeout settings."
            )

        # Success rate recommendations
        if success_rate < 95.0:
            recommendations.append(
                f"Low success rate ({success_rate:.1f}%). "
                "Investigate error handling and retry mechanisms."
            )

        # Throughput recommendations
        if scenario == TestScenario.STRESS_TEST and requests_per_second < 2.0:
            recommendations.append(
                f"Low throughput under stress ({requests_per_second:.2f} req/s). "
                "Consider optimizing concurrent processing or increasing resource limits."
            )

        # Error-specific recommendations
        if "Timeout" in error_breakdown and error_breakdown["Timeout"] > 0:
            recommendations.append(
                f"Timeout errors detected ({error_breakdown['Timeout']} occurrences). "
                "Consider increasing request timeout or optimizing slow operations."
            )

        if "Server Error" in error_breakdown and error_breakdown["Server Error"] > 0:
            recommendations.append(
                f"Server errors detected ({error_breakdown['Server Error']} occurrences). "
                "Check server logs for internal errors and resource exhaustion."
            )

        if (
            "Connection Error" in error_breakdown
            and error_breakdown["Connection Error"] > 0
        ):
            recommendations.append(
                f"Connection errors detected ({error_breakdown['Connection Error']} occurrences). "
                "Check network stability and connection pool settings."
            )

        # Scenario-specific recommendations
        if scenario == TestScenario.SINGLE_USER_MULTIPLE_PAGES:
            if avg_response_time > 3.0:
                recommendations.append(
                    "For single-user multi-page requests, response times should be under 3 seconds. "
                    "Verify browser context reuse and concurrent page processing."
                )

        elif scenario == TestScenario.MULTIPLE_USERS_STANDARD_LOAD:
            if success_rate < 98.0:
                recommendations.append(
                    "Standard load should maintain >98% success rate. "
                    "Check resource contention and error handling."
                )

        elif scenario == TestScenario.STRESS_TEST:
            if success_rate < 90.0:
                recommendations.append(
                    "Stress test success rate is below acceptable threshold. "
                    "System may need additional capacity or better resource management."
                )

        # General recommendations if no issues found
        if not recommendations:
            recommendations.append(
                "Performance looks good! All metrics are within acceptable ranges."
            )

        return recommendations


class PerformanceReporter:
    """
    Comprehensive performance reporting system for load test results.

    This class provides detailed performance report generation with response times,
    success rates, error analysis, and actionable recommendations based on
    performance test results.
    """

    @staticmethod
    def generate_console_report(report: LoadTestReport) -> str:
        """
        Generate a detailed console report for immediate viewing.

        Args:
            report: LoadTestReport to generate report from

        Returns:
            Formatted string report for console output
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"LOAD TEST REPORT - {report.scenario.upper()}")
        lines.append("=" * 80)
        lines.append("")

        # Test overview
        lines.append("TEST OVERVIEW")
        lines.append("-" * 40)
        lines.append(f"Scenario: {report.scenario}")
        lines.append(f"Start Time: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"End Time: {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Duration: {report.total_duration:.2f} seconds")
        lines.append(f"Concurrent Users: {report.concurrent_users}")
        lines.append("")

        # Request statistics
        lines.append("REQUEST STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Requests: {report.total_requests}")
        lines.append(f"Successful Requests: {report.successful_requests}")
        lines.append(f"Failed Requests: {report.failed_requests}")
        lines.append(f"Success Rate: {report.overall_success_rate:.2f}%")
        lines.append(f"Error Rate: {report.overall_error_rate:.2f}%")
        lines.append(f"Requests per Second: {report.requests_per_second:.2f}")
        lines.append("")

        # Response time analysis
        lines.append("RESPONSE TIME ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Average Response Time: {report.average_response_time:.3f}s")
        lines.append(f"Median Response Time: {report.median_response_time:.3f}s")
        lines.append(f"Min Response Time: {report.min_response_time:.3f}s")
        lines.append(f"Max Response Time: {report.max_response_time:.3f}s")
        lines.append(f"95th Percentile: {report.p95_response_time:.3f}s")
        lines.append(f"99th Percentile: {report.p99_response_time:.3f}s")
        lines.append("")

        # Performance targets analysis
        lines.append("PERFORMANCE TARGETS")
        lines.append("-" * 40)
        target_20_pages = 3.0  # Target: 20 pages in under 3 seconds
        target_success_rate = 95.0

        if report.average_response_time <= target_20_pages:
            lines.append(
                f"✓ Average response time ({report.average_response_time:.2f}s) meets target (<{target_20_pages}s)"
            )
        else:
            lines.append(
                f"✗ Average response time ({report.average_response_time:.2f}s) exceeds target (<{target_20_pages}s)"
            )

        if report.overall_success_rate >= target_success_rate:
            lines.append(
                f"✓ Success rate ({report.overall_success_rate:.1f}%) meets target (>{target_success_rate}%)"
            )
        else:
            lines.append(
                f"✗ Success rate ({report.overall_success_rate:.1f}%) below target (>{target_success_rate}%)"
            )

        lines.append("")

        # Error breakdown
        if report.error_breakdown:
            lines.append("ERROR BREAKDOWN")
            lines.append("-" * 40)
            for error_type, count in sorted(
                report.error_breakdown.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / report.total_requests) * 100
                lines.append(f"{error_type}: {count} ({percentage:.1f}%)")
            lines.append("")

        # Status code breakdown
        if report.status_code_breakdown:
            lines.append("STATUS CODE BREAKDOWN")
            lines.append("-" * 40)
            for status_code, count in sorted(report.status_code_breakdown.items()):
                percentage = (count / report.total_requests) * 100
                lines.append(f"HTTP {status_code}: {count} ({percentage:.1f}%)")
            lines.append("")

        # Per-user performance summary
        lines.append("PER-USER PERFORMANCE SUMMARY")
        lines.append("-" * 40)
        lines.append(
            f"{'User ID':<8} {'Requests':<10} {'Success Rate':<12} {'Avg Time':<10} {'RPS':<8}"
        )
        lines.append("-" * 50)

        for user in report.user_metrics:
            success_rate = (
                (user.successful_requests / user.total_requests) * 100
                if user.total_requests > 0
                else 0
            )
            lines.append(
                f"{user.user_id:<8} {user.total_requests:<10} {success_rate:<11.1f}% {user.average_response_time:<9.3f}s {user.requests_per_second:<7.2f}"
            )

        lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        for i, recommendation in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {recommendation}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(report: LoadTestReport) -> str:
        """
        Generate a JSON report for programmatic analysis.

        Args:
            report: LoadTestReport to generate report from

        Returns:
            JSON string representation of the report
        """
        # Convert dataclass to dictionary with proper serialization
        report_dict = {
            "scenario": report.scenario,
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat(),
            "total_duration": report.total_duration,
            "total_requests": report.total_requests,
            "successful_requests": report.successful_requests,
            "failed_requests": report.failed_requests,
            "overall_success_rate": report.overall_success_rate,
            "overall_error_rate": report.overall_error_rate,
            "average_response_time": report.average_response_time,
            "median_response_time": report.median_response_time,
            "p95_response_time": report.p95_response_time,
            "p99_response_time": report.p99_response_time,
            "min_response_time": report.min_response_time,
            "max_response_time": report.max_response_time,
            "requests_per_second": report.requests_per_second,
            "concurrent_users": report.concurrent_users,
            "user_metrics": [asdict(user) for user in report.user_metrics],
            "error_breakdown": report.error_breakdown,
            "status_code_breakdown": report.status_code_breakdown,
            "recommendations": report.recommendations,
            "request_results": [
                asdict(result) for result in report.all_request_results
            ],
        }

        return json.dumps(report_dict, indent=2, default=str)

    @staticmethod
    def generate_csv_summary(report: LoadTestReport) -> str:
        """
        Generate a CSV summary for spreadsheet analysis.

        Args:
            report: LoadTestReport to generate CSV from

        Returns:
            CSV string with summary metrics
        """
        lines = []

        # Header
        lines.append("Metric,Value,Unit")

        # Basic metrics
        lines.append(f"Scenario,{report.scenario},")
        lines.append(f"Total Duration,{report.total_duration:.2f},seconds")
        lines.append(f"Concurrent Users,{report.concurrent_users},count")
        lines.append(f"Total Requests,{report.total_requests},count")
        lines.append(f"Successful Requests,{report.successful_requests},count")
        lines.append(f"Failed Requests,{report.failed_requests},count")
        lines.append(f"Success Rate,{report.overall_success_rate:.2f},%")
        lines.append(f"Error Rate,{report.overall_error_rate:.2f},%")
        lines.append(f"Requests per Second,{report.requests_per_second:.2f},req/s")

        # Response time metrics
        lines.append(
            f"Average Response Time,{report.average_response_time:.3f},seconds"
        )
        lines.append(f"Median Response Time,{report.median_response_time:.3f},seconds")
        lines.append(f"Min Response Time,{report.min_response_time:.3f},seconds")
        lines.append(f"Max Response Time,{report.max_response_time:.3f},seconds")
        lines.append(
            f"95th Percentile Response Time,{report.p95_response_time:.3f},seconds"
        )
        lines.append(
            f"99th Percentile Response Time,{report.p99_response_time:.3f},seconds"
        )

        return "\n".join(lines)

    @staticmethod
    def save_detailed_results(
        report: LoadTestReport, output_dir: str = "load_test_results"
    ):
        """
        Save comprehensive test results to files.

        Args:
            report: LoadTestReport to save
            output_dir: Directory to save results in
        """
        import os

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate timestamp for unique filenames
        timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
        scenario_name = report.scenario.replace(" ", "_").lower()

        # Save console report
        console_report = PerformanceReporter.generate_console_report(report)
        with open(f"{output_dir}/{scenario_name}_{timestamp}_report.txt", "w") as f:
            f.write(console_report)

        # Save JSON report
        json_report = PerformanceReporter.generate_json_report(report)
        with open(f"{output_dir}/{scenario_name}_{timestamp}_data.json", "w") as f:
            f.write(json_report)

        # Save CSV summary
        csv_summary = PerformanceReporter.generate_csv_summary(report)
        with open(f"{output_dir}/{scenario_name}_{timestamp}_summary.csv", "w") as f:
            f.write(csv_summary)

        # Save detailed request results as CSV
        if report.all_request_results:
            lines = [
                "endpoint,method,status_code,response_time,success,error_message,response_size,user_id,timestamp"
            ]
            for result in report.all_request_results:
                lines.append(
                    f"{result.endpoint},{result.method},{result.status_code},"
                    f"{result.response_time:.3f},{result.success},"
                    f'"{result.error_message or ""}",{result.response_size},'
                    f"{result.user_id},{result.timestamp}"
                )

            with open(
                f"{output_dir}/{scenario_name}_{timestamp}_requests.csv", "w"
            ) as f:
                f.write("\n".join(lines))

        print(f"[INFO] Test results saved to {output_dir}/")
        print(
            f"       - {scenario_name}_{timestamp}_report.txt (human-readable report)"
        )
        print(f"       - {scenario_name}_{timestamp}_data.json (complete data)")
        print(f"       - {scenario_name}_{timestamp}_summary.csv (metrics summary)")
        print(
            f"       - {scenario_name}_{timestamp}_requests.csv (detailed request data)"
        )


class LoadTestRunner:
    """
    Main runner class for executing comprehensive load tests.

    This class orchestrates the execution of different test scenarios and
    provides a unified interface for running performance validation tests.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the load test runner.

        Args:
            base_url: Base URL of the API to test
        """
        self.base_url = base_url
        self.tester = LoadTester(base_url)

    async def run_comprehensive_test_suite(
        self, save_results: bool = True, output_dir: str = "load_test_results"
    ) -> Dict[str, LoadTestReport]:
        """
        Run a comprehensive test suite covering all scenarios.

        This method executes all test scenarios and provides comprehensive
        coverage for various query patterns and page counts as required
        by the specifications.

        Args:
            save_results: Whether to save results to files
            output_dir: Directory to save results in

        Returns:
            Dictionary mapping scenario names to LoadTestReport objects
        """
        print("[INFO] Starting comprehensive load test suite...")

        results = {}

        async with self.tester:
            # Test 1: Single user with multiple page counts
            print("\n" + "=" * 60)
            print("TEST 1: Single User Multiple Pages")
            print("=" * 60)
            results[
                "single_user"
            ] = await self.tester.run_single_user_multiple_pages_test()

            # Test 2: Multiple users standard load
            print("\n" + "=" * 60)
            print("TEST 2: Multiple Users Standard Load")
            print("=" * 60)
            results[
                "standard_load"
            ] = await self.tester.run_multiple_users_standard_load_test()

            # Test 3: Stress test
            print("\n" + "=" * 60)
            print("TEST 3: Stress Test")
            print("=" * 60)
            results["stress_test"] = await self.tester.run_stress_test()

            # Test 4: Mixed workload
            print("\n" + "=" * 60)
            print("TEST 4: Mixed Workload")
            print("=" * 60)
            results["mixed_workload"] = await self.tester.run_mixed_workload_test()

        # Generate and display reports
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUITE RESULTS")
        print("=" * 80)

        for scenario_name, report in results.items():
            print(f"\n{scenario_name.upper()} SUMMARY:")
            print(f"  Success Rate: {report.overall_success_rate:.1f}%")
            print(f"  Average Response Time: {report.average_response_time:.2f}s")
            print(f"  P95 Response Time: {report.p95_response_time:.2f}s")
            print(f"  Requests per Second: {report.requests_per_second:.2f}")
            print(f"  Total Requests: {report.total_requests}")

            # Check performance targets
            if report.average_response_time <= 3.0:
                print("  ✓ Performance target met (avg response time < 3s)")
            else:
                print("  ✗ Performance target missed (avg response time > 3s)")

        # Save results if requested
        if save_results:
            for scenario_name, report in results.items():
                PerformanceReporter.save_detailed_results(report, output_dir)

        # Generate overall recommendations
        overall_recommendations = self._generate_overall_recommendations(results)
        print("\nOVERALL RECOMMENDATIONS:")
        for i, rec in enumerate(overall_recommendations, 1):
            print(f"{i}. {rec}")

        return results

    def _generate_overall_recommendations(
        self, results: Dict[str, LoadTestReport]
    ) -> List[str]:
        """Generate overall recommendations based on all test results"""
        recommendations = []

        # Analyze overall performance trends
        avg_response_times = [
            report.average_response_time for report in results.values()
        ]
        success_rates = [report.overall_success_rate for report in results.values()]

        overall_avg_response = statistics.mean(avg_response_times)
        overall_success_rate = statistics.mean(success_rates)

        if overall_avg_response > 3.0:
            recommendations.append(
                f"Overall average response time ({overall_avg_response:.2f}s) exceeds target. "
                "Consider increasing browser context pool size or optimizing concurrent processing."
            )

        if overall_success_rate < 95.0:
            recommendations.append(
                f"Overall success rate ({overall_success_rate:.1f}%) is below target. "
                "Investigate error handling and retry mechanisms across all scenarios."
            )

        # Check for consistency across scenarios
        if max(avg_response_times) - min(avg_response_times) > 2.0:
            recommendations.append(
                "Large variation in response times across scenarios. "
                "Some workload patterns may need specific optimization."
            )

        # Stress test specific analysis
        if "stress_test" in results:
            stress_report = results["stress_test"]
            if stress_report.overall_success_rate < 90.0:
                recommendations.append(
                    f"Stress test success rate ({stress_report.overall_success_rate:.1f}%) indicates "
                    "system may struggle under high load. Consider capacity planning."
                )

        if not recommendations:
            recommendations.append(
                "Excellent performance across all test scenarios! "
                "The optimization appears to be working effectively."
            )

        return recommendations


# Convenience function for quick testing
async def run_quick_performance_test(base_url: str = "http://localhost:8000"):
    """
    Run a quick performance test for immediate feedback.

    Args:
        base_url: Base URL of the API to test
    """
    print("[INFO] Running quick performance test...")

    async with LoadTester(base_url) as tester:
        # Quick test with 3 users, 3 requests each
        report = await tester.run_multiple_users_standard_load_test(
            user_count=3, requests_per_user=3
        )

        # Display results
        console_report = PerformanceReporter.generate_console_report(report)
        print(console_report)

        return report


# Main execution for standalone testing
if __name__ == "__main__":
    import sys

    # Allow base URL to be specified as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    print(f"[INFO] Load testing API at: {base_url}")

    # Run comprehensive test suite
    runner = LoadTestRunner(base_url)
    asyncio.run(runner.run_comprehensive_test_suite())
