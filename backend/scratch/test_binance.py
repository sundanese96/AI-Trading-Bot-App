import asyncio
import httpx

async def main():
    try:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=5.0)
            print(resp.status_code)
            print(resp.json())
    except Exception as e:
        print("ERROR:", repr(e))

asyncio.run(main())
