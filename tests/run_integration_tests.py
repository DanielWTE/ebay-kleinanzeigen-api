#!/usr/bin/env python3
"""
Integration test runner for API performance optimization validation.

This script runs comprehensive integration tests to validate:
1. All endpoints work correctly with optimized components
2. 20-page requests complete in under 3 seconds as per performance requirements
3. Concurrent request handling ensures system remains responsive under load
4. Backward compatibility of all existing API endpoints

Usage:
    python tests/run_integration_tests.py [options]

Options:
    --quick         Run quick validation tests only
    --performance   Run performance validation only
    --full          Run complete integration test suite (default)
    --url URL       Specify API base URL (default: http://localhost:8000)
    --help          Show this help message
"""

import sys
import asyncio
import argparse
import time
from pathlib import Path
import aiohttp
from tests.test_integration import run_comprehensive_integration_tests
from tests.test_performance_validation import run_performance_validation

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules


async def check_api_availability(base_url: str) -> bool:
    """Check if the API is available before running tests"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("browser_status") == "optimized"
                return False
    except Exception as e:
        print(f"❌ API not available at {base_url}: {str(e)}")
        return False


async def run_quick_tests():
    """Run quick validation tests"""
    print("Running quick integration tests...")

    # Import specific test functions for quick testing
    from tests.test_integration import (
        test_root_endpoint,
        test_inserate_endpoint_functionality,
        test_20_page_performance_requirement,
    )

    try:
        await test_root_endpoint()
        await test_inserate_endpoint_functionality()
        await test_20_page_performance_requirement()

        print("\n✅ Quick tests completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Quick tests failed: {str(e)}")
        return False


async def run_performance_tests():
    """Run performance validation tests only"""
    print("Running performance validation tests...")

    try:
        success = await run_performance_validation()

        if success:
            print("\n✅ Performance tests completed successfully!")
        else:
            print("\n❌ Performance tests failed!")

        return success

    except Exception as e:
        print(f"\n❌ Performance tests failed: {str(e)}")
        return False


async def run_full_tests():
    """Run complete integration test suite"""
    print("Running full integration test suite...")

    try:
        # Run comprehensive integration tests
        integration_success = await run_comprehensive_integration_tests()

        print("\n" + "=" * 80)
        print("RUNNING PERFORMANCE VALIDATION")
        print("=" * 80)

        # Run performance validation
        performance_success = await run_performance_validation()

        overall_success = integration_success and performance_success

        print("\n" + "=" * 80)
        print("FINAL TEST RESULTS")
        print("=" * 80)

        if overall_success:
            print("🎉 ALL TESTS PASSED!")
            print(
                "The API optimization is working correctly and meets all requirements."
            )
        else:
            print("❌ SOME TESTS FAILED!")
            print("Review the test output above for details on failures.")

        print("=" * 80)

        return overall_success

    except Exception as e:
        print(f"\n❌ Full test suite failed: {str(e)}")
        return False


def print_help():
    """Print help message"""
    print(__doc__)


async def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description="Integration test runner for API performance optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--quick", action="store_true", help="Run quick validation tests only"
    )

    parser.add_argument(
        "--performance", action="store_true", help="Run performance validation only"
    )

    parser.add_argument(
        "--full", action="store_true", help="Run complete integration test suite"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    # Default to full tests if no specific test type is specified
    if not (args.quick or args.performance or args.full):
        args.full = True

    print("=" * 80)
    print("API PERFORMANCE OPTIMIZATION - INTEGRATION TEST RUNNER")
    print("=" * 80)
    print(f"API URL: {args.url}")

    # Check API availability
    print("Checking API availability...")
    if not await check_api_availability(args.url):
        print("❌ API is not available or not optimized. Please ensure:")
        print("   1. The API server is running")
        print("   2. The optimized browser manager is initialized")
        print("   3. The URL is correct")
        return False

    print("✅ API is available and optimized")

    # Set base URL for test modules (if they support it)
    # Note: This would require modifying the test modules to accept base_url parameter

    start_time = time.time()
    success = False

    try:
        if args.quick:
            success = await run_quick_tests()
        elif args.performance:
            success = await run_performance_tests()
        elif args.full:
            success = await run_full_tests()

        total_time = time.time() - start_time

        print(f"\nTotal execution time: {total_time:.2f} seconds")

        return success

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
