import asyncio
import httpx
async def main():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers, timeout=10.0)
        print(f"Status: {response.status_code}")
        print(response.text[:200])
asyncio.run(main())
