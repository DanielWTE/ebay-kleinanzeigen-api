#!/usr/bin/env python3
"""
Example script for running load tests against the Kleinanzeigen API.

This script demonstrates how to use the LoadTester framework to validate
API performance under different load conditions. It provides examples
of running individual test scenarios as well as comprehensive test suites.

Usage:
    python tests/run_load_tests.py [base_url]

Examples:
    python tests/run_load_tests.py
    python tests/run_load_tests.py http://localhost:8000
    python tests/run_load_tests.py https://api.example.com
"""

import asyncio
import argparse
from load_test import (
    LoadTester,
    LoadTestRunner,
    run_quick_performance_test,
)


async def run_individual_scenario_example():
    """Example of running individual test scenarios"""
    base_url = "http://localhost:8000"

    print("=" * 80)
    print("INDIVIDUAL SCENARIO EXAMPLES")
    print("=" * 80)

    async with LoadTester(base_url) as tester:
        # Example 1: Single user with varying page counts
        print("\n1. Testing single user with multiple page counts...")
        single_user_report = await tester.run_single_user_multiple_pages_test(
            page_counts=[1, 5, 10, 20], iterations=2
        )

        print("Single User Test Results:")
        print(
            f"  Average Response Time: {single_user_report.average_response_time:.2f}s"
        )
        print(f"  Success Rate: {single_user_report.overall_success_rate:.1f}%")

        # Example 2: Multiple users standard load
        print("\n2. Testing multiple users with standard load...")
        standard_load_report = await tester.run_multiple_users_standard_load_test(
            user_count=5, requests_per_user=4
        )

        print("Standard Load Test Results:")
        print(
            f"  Average Response Time: {standard_load_report.average_response_time:.2f}s"
        )
        print(f"  Success Rate: {standard_load_report.overall_success_rate:.1f}%")
        print(f"  Requests per Second: {standard_load_report.requests_per_second:.2f}")

        # Example 3: Custom concurrent user simulation
        print("\n3. Testing custom concurrent user simulation...")
        from load_test import TestScenario

        user_metrics = await tester.simulate_concurrent_users(
            user_count=3,
            requests_per_user=5,
            scenario=TestScenario.MIXED_WORKLOAD,
            delay_between_requests=0.2,
        )

        print("Custom Simulation Results:")
        for user in user_metrics:
            print(
                f"  User {user.user_id}: {user.successful_requests}/{user.total_requests} "
                f"successful ({user.error_rate:.1f}% error rate)"
            )


async def run_comprehensive_suite_example():
    """Example of running the comprehensive test suite"""
    base_url = "http://localhost:8000"

    print("=" * 80)
    print("COMPREHENSIVE TEST SUITE EXAMPLE")
    print("=" * 80)

    runner = LoadTestRunner(base_url)
    results = await runner.run_comprehensive_test_suite(
        save_results=True, output_dir="example_load_test_results"
    )

    # Display summary of all results
    print("\nCOMPREHENSIVE RESULTS SUMMARY:")
    print("-" * 50)

    for scenario_name, report in results.items():
        print(f"\n{scenario_name.upper()}:")
        print(f"  Duration: {report.total_duration:.1f}s")
        print(f"  Total Requests: {report.total_requests}")
        print(f"  Success Rate: {report.overall_success_rate:.1f}%")
        print(f"  Avg Response Time: {report.average_response_time:.2f}s")
        print(f"  P95 Response Time: {report.p95_response_time:.2f}s")
        print(f"  Throughput: {report.requests_per_second:.2f} req/s")

        # Show top recommendations
        if report.recommendations:
            print(f"  Top Recommendation: {report.recommendations[0]}")


async def run_performance_validation():
    """Example of validating specific performance requirements"""
    base_url = "http://localhost:8000"

    print("=" * 80)
    print("PERFORMANCE VALIDATION EXAMPLE")
    print("=" * 80)

    async with LoadTester(base_url) as tester:
        # Test the specific requirement: 20-page requests in under 3 seconds
        print("\nValidating 20-page request performance requirement...")

        # Create a custom test for 20-page requests
        results = []
        for i in range(3):  # Test 3 times for consistency
            params = {"query": "laptop", "location": "Berlin", "page_count": 20}

            result = await tester.make_request("/inserate", params, user_id=i)
            results.append(result)
            print(
                f"  Test {i + 1}: {result.response_time:.2f}s ({'✓' if result.success and result.response_time < 3.0 else '✗'})"
            )

        # Calculate average
        successful_results = [r for r in results if r.success]
        if successful_results:
            avg_time = sum(r.response_time for r in successful_results) / len(
                successful_results
            )
            print(f"\nAverage 20-page response time: {avg_time:.2f}s")

            if avg_time < 3.0:
                print(
                    "✓ PERFORMANCE REQUIREMENT MET: 20-page requests complete in under 3 seconds"
                )
            else:
                print(
                    "✗ PERFORMANCE REQUIREMENT NOT MET: 20-page requests exceed 3 seconds"
                )
        else:
            print("✗ PERFORMANCE TEST FAILED: No successful requests")


async def run_custom_test_patterns():
    """Example of creating custom test patterns"""
    base_url = "http://localhost:8000"

    print("=" * 80)
    print("CUSTOM TEST PATTERNS EXAMPLE")
    print("=" * 80)

    async with LoadTester(base_url) as tester:
        # Custom pattern 1: Test different endpoints
        print("\n1. Testing different endpoint patterns...")

        endpoints_to_test = [
            ("/inserate", {"query": "smartphone", "page_count": 5}),
            ("/inserat/2123456789", {}),
            (
                "/inserate-detailed",
                {"query": "laptop", "page_count": 3, "max_concurrent_details": 5},
            ),
        ]

        for endpoint, params in endpoints_to_test:
            result = await tester.make_request(endpoint, params)
            print(
                f"  {endpoint}: {result.response_time:.2f}s ({'✓' if result.success else '✗'})"
            )

        # Custom pattern 2: Gradual load increase
        print("\n2. Testing gradual load increase...")

        for user_count in [1, 3, 5, 8]:
            user_metrics = await tester.simulate_concurrent_users(
                user_count=user_count, requests_per_user=2, delay_between_requests=0.1
            )

            avg_response_time = sum(
                u.average_response_time for u in user_metrics
            ) / len(user_metrics)
            success_rate = (
                sum(u.successful_requests for u in user_metrics)
                / sum(u.total_requests for u in user_metrics)
                * 100
            )

            print(
                f"  {user_count} users: {avg_response_time:.2f}s avg, {success_rate:.1f}% success"
            )


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Run load tests against the Kleinanzeigen API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --quick                    # Run quick performance test
  %(prog)s --individual               # Run individual scenario examples  
  %(prog)s --comprehensive            # Run comprehensive test suite
  %(prog)s --validation               # Run performance validation
  %(prog)s --custom                   # Run custom test patterns
  %(prog)s --all                      # Run all examples
        """,
    )

    parser.add_argument(
        "base_url",
        nargs="?",
        default="http://localhost:8000",
        help="Base URL of the API to test (default: http://localhost:8000)",
    )

    parser.add_argument(
        "--quick", action="store_true", help="Run quick performance test"
    )

    parser.add_argument(
        "--individual", action="store_true", help="Run individual scenario examples"
    )

    parser.add_argument(
        "--comprehensive", action="store_true", help="Run comprehensive test suite"
    )

    parser.add_argument(
        "--validation", action="store_true", help="Run performance validation tests"
    )

    parser.add_argument(
        "--custom", action="store_true", help="Run custom test pattern examples"
    )

    parser.add_argument("--all", action="store_true", help="Run all example scenarios")

    args = parser.parse_args()

    # If no specific test is requested, run quick test
    if not any(
        [
            args.quick,
            args.individual,
            args.comprehensive,
            args.validation,
            args.custom,
            args.all,
        ]
    ):
        args.quick = True

    print(f"[INFO] Testing API at: {args.base_url}")
    print(f"[INFO] Make sure the API server is running at {args.base_url}")
    print()

    # Run requested tests
    if args.quick or args.all:
        print("Running quick performance test...")
        asyncio.run(run_quick_performance_test(args.base_url))

    if args.individual or args.all:
        print("\nRunning individual scenario examples...")
        asyncio.run(run_individual_scenario_example())

    if args.comprehensive or args.all:
        print("\nRunning comprehensive test suite...")
        asyncio.run(run_comprehensive_suite_example())

    if args.validation or args.all:
        print("\nRunning performance validation...")
        asyncio.run(run_performance_validation())

    if args.custom or args.all:
        print("\nRunning custom test patterns...")
        asyncio.run(run_custom_test_patterns())

    print("\n[INFO] Load testing completed!")


if __name__ == "__main__":
    main()
