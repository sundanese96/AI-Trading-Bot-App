import os
import time
import httpx
import asyncio
import pandas as pd
from pathlib import Path
from backend.config import VERIFY_SSL

DATA_DIR = Path("Train-data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Start timestamp for 2020-01-01 00:00:00 UTC (1577836800000 ms)
START_TS = 1577836800000

async def download_klines(symbol: str):
    """Downloads historical 5m Futures klines for a given symbol."""
    feather_path = DATA_DIR / f"{symbol}_5m.feather"
    checkpoint_path = DATA_DIR / f"{symbol}_download_checkpoint_5m.txt"
    
    print(f"\n=========================================")
    print(f" Starting 5m Kline Download for {symbol}")
    print(f"=========================================")
    
    # 1. Determine local checkpoint or existing records
    start_time = START_TS
    existing_klines = []
    
    if feather_path.exists():
        try:
            df_existing = pd.read_feather(str(feather_path))
            existing_klines = df_existing.to_dict("records")
            print(f"[{symbol}] Loaded {len(existing_klines)} existing records.")
            
            # If checkpoint exists, use it. Otherwise, look at the last record timestamp
            if checkpoint_path.exists():
                with open(checkpoint_path, "r") as f:
                    start_time = int(f.read().strip())
            else:
                last_date = df_existing["date"].iloc[-1]
                start_time = int(pd.to_datetime(last_date).timestamp() * 1000) + 300000
                
            print(f"[{symbol}] Resuming from: {pd.to_datetime(start_time, unit='ms')}")
        except Exception as e:
            print(f"[{symbol}] Error loading existing feather: {e}. Starting fresh.")
    
    end_time_limit = int(time.time() * 1000)
    limit = 1500
    backoff_delay = 2.0
    total_downloaded = 0
    
    async with httpx.AsyncClient(headers=HEADERS, verify=VERIFY_SSL) as client:
        while start_time < end_time_limit:
            params = {
                "symbol": symbol,
                "interval": "5m", 
                "startTime": start_time,
                "limit": limit
            }
            
            try:
                res = await client.get(BINANCE_KLINES_URL, params=params, timeout=20.0)
                
                if res.status_code == 429:
                    print(f"[{symbol}] Rate limit hit (429). Delaying {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(60.0, backoff_delay * 2.0)
                    continue
                else:
                    backoff_delay = 2.0  # Reset
                
                if res.status_code != 200:
                    print(f"[{symbol}] Status {res.status_code}. Response: {res.text}. Retrying...")
                    await asyncio.sleep(3.0)
                    continue
                
                data = res.json()
                if not data:
                    print(f"[{symbol}] Completed. No more data.")
                    break
                
                batch = []
                for k in data:
                    batch.append({
                        "date": pd.to_datetime(k[0], unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                existing_klines.extend(batch)
                total_downloaded += len(batch)
                
                # Update next start time: last timestamp + 5m (300,000 ms)
                last_ts = int(data[-1][0])
                start_time = last_ts + 300000
                
                # Save checkpoint
                with open(checkpoint_path, "w") as f:
                    f.write(str(start_time))
                
                # Periodically save
                if total_downloaded % 15000 == 0 or start_time >= end_time_limit:
                    df = pd.DataFrame(existing_klines)
                    df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
                    df.to_feather(str(feather_path))
                    print(f"[{symbol}] Saved {len(df)} klines to disk. Current date: {batch[-1]['date']}")
                
                # Small sleep to respect rate limits
                await asyncio.sleep(0.02)
                
            except Exception as e:
                print(f"[{symbol}] Exception: {e}")
                await asyncio.sleep(3.0)

async def download_funding_rates(symbol: str):
    """Downloads historical 8h Futures funding rates for a given symbol."""
    feather_path = DATA_DIR / f"{symbol}_funding_rates.feather"
    checkpoint_path = DATA_DIR / f"{symbol}_funding_checkpoint.txt"
    
    print(f"\n=========================================")
    print(f" Starting Funding Rate Download for {symbol}")
    print(f"=========================================")
    
    start_time = START_TS
    existing_rates = []
    
    if feather_path.exists():
        try:
            df_existing = pd.read_feather(str(feather_path))
            existing_rates = df_existing.to_dict("records")
            print(f"[{symbol} Funding] Loaded {len(existing_rates)} records.")
            
            if checkpoint_path.exists():
                with open(checkpoint_path, "r") as f:
                    start_time = int(f.read().strip())
            else:
                last_ts = df_existing["timestamp"].iloc[-1]
                start_time = last_ts + 1000
            print(f"[{symbol} Funding] Resuming from: {pd.to_datetime(start_time, unit='ms')}")
        except Exception as e:
            print(f"[{symbol} Funding] Error: {e}. Starting fresh.")
            
    end_time_limit = int(time.time() * 1000)
    limit = 1000
    backoff_delay = 2.0
    total_downloaded = 0
    
    async with httpx.AsyncClient(headers=HEADERS, verify=VERIFY_SSL) as client:
        while start_time < end_time_limit:
            params = {
                "symbol": symbol,
                "startTime": start_time,
                "limit": limit
            }
            
            try:
                res = await client.get(BINANCE_FUNDING_URL, params=params, timeout=20.0)
                
                if res.status_code == 429:
                    print(f"[{symbol} Funding] 429 Rate limit. Delaying {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(60.0, backoff_delay * 2.0)
                    continue
                else:
                    backoff_delay = 2.0
                    
                if res.status_code != 200:
                    print(f"[{symbol} Funding] Status {res.status_code}. Response: {res.text}")
                    await asyncio.sleep(3.0)
                    continue
                
                data = res.json()
                if not data:
                    print(f"[{symbol} Funding] Completed. No more funding rate records.")
                    break
                
                batch = []
                for rate in data:
                    batch.append({
                        "timestamp": int(rate["fundingTime"]),
                        "date": pd.to_datetime(rate["fundingTime"], unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                        "fundingRate": float(rate["fundingRate"]),
                        "markPrice": float(rate["markPrice"]) if rate["markPrice"] else 0.0
                    })
                
                existing_rates.extend(batch)
                total_downloaded += len(batch)
                
                # Update next start time
                last_ts = int(data[-1]["fundingTime"])
                start_time = last_ts + 1000
                
                # Save checkpoint
                with open(checkpoint_path, "w") as f:
                    f.write(str(start_time))
                
                df = pd.DataFrame(existing_rates)
                df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
                df.to_feather(str(feather_path))
                print(f"[{symbol} Funding] Saved {len(df)} total records. Last timestamp: {batch[-1]['date']}")
                
                await asyncio.sleep(0.02)
                
            except Exception as e:
                print(f"[{symbol} Funding] Exception: {e}")
                await asyncio.sleep(3.0)

async def main():
    funding_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    kline_symbols = ["ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    # 1. Download Funding Rates concurrently
    print("Downloading Funding Rates concurrently...")
    await asyncio.gather(*(download_funding_rates(s) for s in funding_symbols))
    
    # 2. Download 5m Klines concurrently
    print("\nDownloading 5m Klines concurrently...")
    await asyncio.gather(*(download_klines(s) for s in kline_symbols))

if __name__ == "__main__":
    asyncio.run(main())