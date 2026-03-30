"""
Debug script to check API responses and identify issues.
"""

import asyncio
import aiohttp
import json


async def debug_api():
    """Debug API responses"""
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Test inserate-detailed endpoint
        print("Testing /inserate-detailed endpoint...")

        try:
            async with session.get(
                f"{base_url}/inserate-detailed",
                params={"query": "test", "page_count": 1},
            ) as response:
                print(f"Status: {response.status}")

                try:
                    data = await response.json()
                    print("Response data:")
                    print(json.dumps(data, indent=2))
                except Exception as e:
                    text = await response.text()
                    print(f"Failed to parse JSON: {e}")
                    print(f"Raw response: {text}")

        except Exception as e:
            print(f"Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_api())
