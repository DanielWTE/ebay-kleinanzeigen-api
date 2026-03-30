"""
Simple test to check individual endpoints
"""

import asyncio
import aiohttp


async def test_endpoints():
    """Test each endpoint individually"""
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Test inserate endpoint
        print("Testing /inserate...")
        try:
            async with session.get(
                f"{base_url}/inserate", params={"query": "test", "page_count": 1}
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Success: {data.get('success')}")
                    print(f"Results: {data.get('unique_results', 0)}")
        except Exception as e:
            print(f"Error: {e}")

        print("\nTesting /inserate-detailed...")
        try:
            async with session.get(
                f"{base_url}/inserate-detailed",
                params={"query": "test", "page_count": 1, "max_concurrent_details": 2},
            ) as response:
                print(f"Status: {response.status}")
                text = await response.text()
                print(f"Response length: {len(text)}")
                if text.strip():
                    try:
                        data = await response.json()
                        print(
                            f"Success: {data.get('success') if data else 'null response'}"
                        )
                    except Exception:
                        print(f"Raw response: {text[:200]}...")
                else:
                    print("Empty response")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
