import asyncio
import httpx
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

async def test_connection():
    print(f"Testing connection to {API_BASE_URL}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/sessions")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            if response.status_code == 200:
                print("✅ Connection successful!")
            else:
                print(f"❌ Connection failed with status code {response.status_code}")
    except Exception as e:
        print(f"❌ Connection failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
