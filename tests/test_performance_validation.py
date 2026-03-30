"""
Performance validation script for API optimization requirements.

This script specifically validates the core performance requirement:
- 20-page requests must complete in under 3 seconds (Requirement 1.1)

It also validates related performance requirements:
- System remains responsive under concurrent load (Requirements 3.1, 3.2)
- Performance metrics are accurate and comprehensive
"""

import asyncio
import time
import statistics
import aiohttp
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class PerformanceTestResult:
    """Performance test result with detailed metrics"""

    test_name: str
    success: bool
    response_time: float
    requirement_met: bool
    response_data: Dict[str, Any]
    error_message: str = None


class PerformanceValidator:
    """Validates API performance against specific requirements"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=60
            )  # Longer timeout for performance tests
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def validate_20_page_requirement(self, iterations: int = 5) -> Dict[str, Any]:
        """
        Validate that 20-page requests complete in under 3 seconds.

        This is the core performance requirement (1.1) that the optimization
        was designed to achieve.
        """
        print(
            f"Validating 20-page performance requirement ({iterations} iterations)..."
        )

        results = []
        params = {"query": "laptop", "page_count": 20}

        for i in range(iterations):
            print(f"  Iteration {i + 1}/{iterations}...", end=" ")

            start_time = time.time()
            try:
                async with self.session.get(
                    f"{self.base_url}/inserate", params=params
                ) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        response_data = await response.json()

                        result = PerformanceTestResult(
                            test_name=f"20_page_test_iteration_{i + 1}",
                            success=True,
                            response_time=response_time,
                            requirement_met=response_time < 3.0,
                            response_data=response_data,
                        )

                        print(
                            f"{response_time:.3f}s {'✓' if response_time < 3.0 else '✗'}"
                        )
                    else:
                        result = PerformanceTestResult(
                            test_name=f"20_page_test_iteration_{i + 1}",
                            success=False,
                            response_time=response_time,
                            requirement_met=False,
                            response_data={},
                            error_message=f"HTTP {response.status}",
                        )
                        print(f"FAILED (HTTP {response.status})")

                    results.append(result)

            except Exception as e:
                response_time = time.time() - start_time
                result = PerformanceTestResult(
                    test_name=f"20_page_test_iteration_{i + 1}",
                    success=False,
                    response_time=response_time,
                    requirement_met=False,
                    response_data={},
                    error_message=str(e),
                )
                results.append(result)
                print(f"ERROR: {str(e)}")

        # Analyze results
        successful_results = [r for r in results if r.success]

        if not successful_results:
            return {
                "requirement_met": False,
                "error": "All iterations failed",
                "results": results,
            }

        response_times = [r.response_time for r in successful_results]
        requirements_met = [r.requirement_met for r in successful_results]

        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        median_time = statistics.median(response_times)

        success_rate = len(successful_results) / len(results) * 100
        requirement_success_rate = sum(requirements_met) / len(requirements_met) * 100

        # Get performance metrics from last successful result
        last_successful = successful_results[-1]
        perf_metrics = last_successful.response_data.get("performance_metrics", {})

        return {
            "requirement_met": requirement_success_rate
            >= 80.0,  # 80% of tests should meet requirement
            "success_rate": success_rate,
            "requirement_success_rate": requirement_success_rate,
            "statistics": {
                "average_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "median_time": median_time,
                "target_time": 3.0,
            },
            "performance_metrics": perf_metrics,
            "iterations": iterations,
            "successful_iterations": len(successful_results),
            "results": results,
        }

    async def validate_concurrent_performance(self) -> Dict[str, Any]:
        """
        Validate that system remains responsive under concurrent load.

        Tests Requirements 3.1 and 3.2:
        - Multiple clients can make simultaneous requests
        - Response times don't exceed 5 seconds under load
        """
        print("Validating concurrent performance...")

        async def make_concurrent_request(
            user_id: int, request_id: int
        ) -> PerformanceTestResult:
            """Make a single request as part of concurrent test"""
            params = {"query": "smartphone", "page_count": 5}

            start_time = time.time()
            try:
                async with self.session.get(
                    f"{self.base_url}/inserate", params=params
                ) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        response_data = await response.json()
                        return PerformanceTestResult(
                            test_name=f"concurrent_user_{user_id}_request_{request_id}",
                            success=True,
                            response_time=response_time,
                            requirement_met=response_time
                            < 5.0,  # 5 second limit under load
                            response_data=response_data,
                        )
                    else:
                        return PerformanceTestResult(
                            test_name=f"concurrent_user_{user_id}_request_{request_id}",
                            success=False,
                            response_time=response_time,
                            requirement_met=False,
                            response_data={},
                            error_message=f"HTTP {response.status}",
                        )

            except Exception as e:
                response_time = time.time() - start_time
                return PerformanceTestResult(
                    test_name=f"concurrent_user_{user_id}_request_{request_id}",
                    success=False,
                    response_time=response_time,
                    requirement_met=False,
                    response_data={},
                    error_message=str(e),
                )

        # Create concurrent tasks: 6 users, 3 requests each
        concurrent_users = 6
        requests_per_user = 3

        tasks = []
        for user_id in range(concurrent_users):
            for request_id in range(requests_per_user):
                task = make_concurrent_request(user_id, request_id)
                tasks.append(task)

        print(
            f"  Running {len(tasks)} concurrent requests ({concurrent_users} users, {requests_per_user} requests each)..."
        )

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Process results
        valid_results = [r for r in results if isinstance(r, PerformanceTestResult)]
        successful_results = [r for r in valid_results if r.success]

        if not successful_results:
            return {
                "requirement_met": False,
                "error": "All concurrent requests failed",
                "total_time": total_time,
            }

        response_times = [r.response_time for r in successful_results]
        requirements_met = [r.requirement_met for r in successful_results]

        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        success_rate = len(successful_results) / len(valid_results) * 100
        requirement_success_rate = sum(requirements_met) / len(requirements_met) * 100

        print(f"  Completed in {total_time:.2f}s")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_time:.3f}s")
        print(f"  Max response time: {max_time:.3f}s")

        return {
            "requirement_met": success_rate >= 90.0 and max_time <= 5.0,
            "success_rate": success_rate,
            "requirement_success_rate": requirement_success_rate,
            "statistics": {
                "average_time": avg_time,
                "max_time": max_time,
                "target_max_time": 5.0,
                "total_concurrent_time": total_time,
            },
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(valid_results),
            "successful_requests": len(successful_results),
        }

    async def validate_performance_metrics_accuracy(self) -> Dict[str, Any]:
        """
        Validate that performance metrics in API responses are accurate and comprehensive.

        This ensures the optimization provides proper visibility into system performance.
        """
        print("Validating performance metrics accuracy...")

        params = {"query": "tablet", "page_count": 10}

        start_time = time.time()
        async with self.session.get(
            f"{self.base_url}/inserate", params=params
        ) as response:
            actual_response_time = time.time() - start_time

            if response.status != 200:
                return {
                    "valid": False,
                    "error": f"Request failed with status {response.status}",
                }

            response_data = await response.json()

            # Check if performance metrics are present
            if "performance_metrics" not in response_data:
                return {"valid": False, "error": "No performance_metrics in response"}

            perf_metrics = response_data["performance_metrics"]
            reported_time = response_data.get("time_taken", 0)

            # Validate metric fields
            required_fields = [
                "pages_requested",
                "pages_successful",
                "pages_failed",
                "concurrent_level",
                "page_details",
            ]

            missing_fields = [
                field for field in required_fields if field not in perf_metrics
            ]

            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing performance metric fields: {missing_fields}",
                }

            # Validate metric accuracy
            time_difference = abs(actual_response_time - reported_time)
            time_accuracy = time_difference < 0.5  # Within 500ms is acceptable

            pages_requested = perf_metrics["pages_requested"]
            pages_successful = perf_metrics["pages_successful"]
            pages_failed = perf_metrics["pages_failed"]

            # Validate page counts
            page_count_valid = (pages_successful + pages_failed) == pages_requested
            pages_requested_correct = pages_requested == params["page_count"]

            return {
                "valid": time_accuracy and page_count_valid and pages_requested_correct,
                "time_accuracy": time_accuracy,
                "time_difference": time_difference,
                "actual_time": actual_response_time,
                "reported_time": reported_time,
                "page_count_valid": page_count_valid,
                "pages_requested_correct": pages_requested_correct,
                "performance_metrics": perf_metrics,
                "missing_fields": missing_fields,
            }


async def run_performance_validation():
    """Run comprehensive performance validation"""
    print("=" * 80)
    print("API PERFORMANCE VALIDATION SUITE")
    print("Validating optimization requirements")
    print("=" * 80)

    async with PerformanceValidator() as validator:
        all_passed = True

        # Test 1: 20-page performance requirement (Core requirement 1.1)
        print("\n1. TESTING 20-PAGE PERFORMANCE REQUIREMENT")
        print("-" * 50)

        result_20_page = await validator.validate_20_page_requirement(iterations=5)

        if result_20_page["requirement_met"]:
            print("✓ 20-page performance requirement PASSED")
        else:
            print("✗ 20-page performance requirement FAILED")
            all_passed = False

        stats = result_20_page["statistics"]
        print(
            f"  Average time: {stats['average_time']:.3f}s (target: <{stats['target_time']}s)"
        )
        print(f"  Min time: {stats['min_time']:.3f}s")
        print(f"  Max time: {stats['max_time']:.3f}s")
        print(f"  Median time: {stats['median_time']:.3f}s")
        print(f"  Success rate: {result_20_page['success_rate']:.1f}%")
        print(
            f"  Requirement success rate: {result_20_page['requirement_success_rate']:.1f}%"
        )

        # Test 2: Concurrent performance (Requirements 3.1, 3.2)
        print("\n2. TESTING CONCURRENT PERFORMANCE")
        print("-" * 50)

        result_concurrent = await validator.validate_concurrent_performance()

        if result_concurrent["requirement_met"]:
            print("✓ Concurrent performance requirement PASSED")
        else:
            print("✗ Concurrent performance requirement FAILED")
            all_passed = False

        stats = result_concurrent["statistics"]
        print(f"  Success rate: {result_concurrent['success_rate']:.1f}%")
        print(f"  Average response time: {stats['average_time']:.3f}s")
        print(
            f"  Max response time: {stats['max_time']:.3f}s (target: <{stats['target_max_time']}s)"
        )
        print(f"  Total concurrent requests: {result_concurrent['total_requests']}")
        print(f"  Concurrent users: {result_concurrent['concurrent_users']}")

        # Test 3: Performance metrics accuracy
        print("\n3. TESTING PERFORMANCE METRICS ACCURACY")
        print("-" * 50)

        result_metrics = await validator.validate_performance_metrics_accuracy()

        if result_metrics["valid"]:
            print("✓ Performance metrics accuracy PASSED")
        else:
            print("✗ Performance metrics accuracy FAILED")
            all_passed = False

        if result_metrics.get("time_accuracy"):
            print(
                f"  Time accuracy: ✓ (difference: {result_metrics['time_difference']:.3f}s)"
            )
        else:
            print(
                f"  Time accuracy: ✗ (difference: {result_metrics['time_difference']:.3f}s)"
            )

        if result_metrics.get("page_count_valid"):
            print("  Page count validation: ✓")
        else:
            print("  Page count validation: ✗")

        # Summary
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ALL PERFORMANCE REQUIREMENTS PASSED")
            print("The API optimization successfully meets all performance targets!")
        else:
            print("❌ SOME PERFORMANCE REQUIREMENTS FAILED")
            print("Review the failed tests above for optimization opportunities.")

        print("=" * 80)

        return all_passed


if __name__ == "__main__":
    # Run performance validation
    success = asyncio.run(run_performance_validation())
    exit(0 if success else 1)
