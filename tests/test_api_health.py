"""
API health check test to verify the server is running and optimized components are working.

This test validates:
- API server is accessible
- Optimized browser manager is initialized
- All endpoints are available
- Basic functionality works
"""

import asyncio
import aiohttp
import time


async def test_api_health(base_url: str = "http://localhost:8000"):
    """Test API health and optimization status"""
    print("Testing API health and optimization status...")

    async with aiohttp.ClientSession() as session:
        try:
            # Test 1: Root endpoint
            print("  Testing root endpoint...", end=" ")
            async with session.get(f"{base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("browser_status") == "optimized":
                        print("✅ OK (optimized)")
                    else:
                        print(
                            f"⚠️  Browser status: {data.get('browser_status', 'unknown')}"
                        )
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False

            # Test 2: Inserate endpoint basic functionality
            print("  Testing /inserate endpoint...", end=" ")
            start_time = time.time()
            async with session.get(
                f"{base_url}/inserate", params={"query": "test", "page_count": 1}
            ) as response:
                response_time = time.time() - start_time
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        print(f"✅ OK ({response_time:.3f}s)")
                    else:
                        print(f"⚠️  Success: {data.get('success')}")
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False

            # Test 3: Inserate-detailed endpoint
            print("  Testing /inserate-detailed endpoint...", end=" ")
            start_time = time.time()
            async with session.get(
                f"{base_url}/inserate-detailed",
                params={"query": "test", "page_count": 1},
            ) as response:
                response_time = time.time() - start_time
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        print(f"✅ OK ({response_time:.3f}s)")
                    else:
                        print(f"⚠️  Success: {data.get('success')}")
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False

            # Test 4: Performance metrics presence
            print("  Checking performance metrics...", end=" ")
            async with session.get(
                f"{base_url}/inserate", params={"query": "laptop", "page_count": 2}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "performance_metrics" in data:
                        perf_metrics = data["performance_metrics"]
                        required_fields = [
                            "pages_requested",
                            "pages_successful",
                            "concurrent_level",
                        ]
                        if all(field in perf_metrics for field in required_fields):
                            print("✅ OK")
                        else:
                            print("⚠️  Missing performance metric fields")
                            return False
                    else:
                        print("⚠️  No performance metrics in response")
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False

            print("\n✅ API health check passed - All systems operational!")
            return True

        except Exception as e:
            print(f"\n❌ API health check failed: {str(e)}")
            return False


async def main():
    """Run API health check"""
    print("=" * 60)
    print("API HEALTH CHECK")
    print("=" * 60)

    success = await test_api_health()

    if success:
        print("\n🎉 API is healthy and ready for integration tests!")
    else:
        print("\n❌ API health check failed. Please check:")
        print("   1. API server is running (python main.py)")
        print("   2. All dependencies are installed")
        print("   3. Browser manager is properly initialized")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
