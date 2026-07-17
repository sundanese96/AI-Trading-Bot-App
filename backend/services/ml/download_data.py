import os
import time
import httpx
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (allows proxy configuration via HTTP_PROXY/HTTPS_PROXY in .env)
load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FEATHER_PATH = DATA_DIR / "BTC_USDT_futures_1m.feather"
CHECKPOINT_PATH = DATA_DIR / "download_checkpoint.txt"

# Binance Futures Public API
BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"

# Browser-like headers to avoid WAF blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_last_checkpoint() -> int:
    """Gets the last downloaded timestamp (in ms) from the checkpoint file."""
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r") as f:
                ts = int(f.read().strip())
                print(f"[Downloader] Resuming from checkpoint: {pd.to_datetime(ts, unit='ms')}")
                return ts
        except Exception as e:
            print(f"[Downloader] Failed to read checkpoint: {e}")
    
    # Default start time: January 1, 2020 (in ms)
    default_start = int(pd.to_datetime("2020-01-01").timestamp() * 1000)
    print(f"[Downloader] No checkpoint found. Starting from default: {pd.to_datetime(default_start, unit='ms')}")
    return default_start

def save_checkpoint(timestamp: int):
    """Saves the last downloaded timestamp to the checkpoint file."""
    try:
        with open(CHECKPOINT_PATH, "w") as f:
            f.write(str(timestamp))
    except Exception as e:
        print(f"[Downloader] Failed to save checkpoint: {e}")

async def download_btc_historical_data():
    """Downloads historical 1m BTC/USDT Futures klines from Binance."""
    start_time = get_last_checkpoint()
    end_time_limit = int(time.time() * 1000) # Current time in ms
    
    all_klines = []
    
    # Load existing data if feather file exists
    if FEATHER_PATH.exists():
        try:
            existing_df = pd.read_feather(str(FEATHER_PATH))
            all_klines = existing_df.to_dict("records")
            print(f"[Downloader] Loaded {len(all_klines)} existing records from feather file.")
        except Exception as e:
            print(f"[Downloader] Failed to load existing feather file: {e}")

    limit = 1500 # Max limit per request
    backoff_delay = 2.0
    
    total_downloaded = 0
    
    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
        while start_time < end_time_limit:
            params = {
                "symbol": "BTCUSDT",
                "interval": "1m",
                "startTime": start_time,
                "limit": limit
            }
            
            try:
                res = await client.get(BINANCE_KLINES_URL, params=params, timeout=15.0)
                
                # Handle Rate Limit (HTTP 429)
                if res.status_code == 429:
                    print(f"[Downloader] Rate limit hit (429). Backing off for {backoff_delay}s...")
                    time.sleep(backoff_delay)
                    backoff_delay = min(60.0, backoff_delay * 2.0)
                    continue
                else:
                    backoff_delay = 2.0 # Reset backoff on success
                    
                if res.status_code != 200:
                    print(f"[Downloader] Error fetching data: Status {res.status_code}, Response: {res.text}")
                    time.sleep(5.0)
                    continue
                    
                data = res.json()
                if not data:
                    print("[Downloader] No more data returned from Binance. Download complete.")
                    break
                    
                # Parse klines
                batch_klines = []
                for k in data:
                    batch_klines.append({
                        "date": pd.to_datetime(k[0], unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                all_klines.extend(batch_klines)
                total_downloaded += len(batch_klines)
                
                # Update start_time to the timestamp of the last candle in the batch + 1 minute
                last_timestamp = int(data[-1][0])
                start_time = last_timestamp + 60000
                
                # Save progress checkpoint
                save_checkpoint(start_time)
                
                # Periodically save to feather file and print progress log
                if total_downloaded % 15000 == 0 or start_time >= end_time_limit:
                    df = pd.DataFrame(all_klines)
                    # Drop duplicates to ensure clean data
                    df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
                    df.to_feather(str(FEATHER_PATH))
                    
                    current_date = batch_klines[-1]["date"]
                    print(f"[Downloader] Progress: Downloaded {len(df)} total candles. Current date: {current_date}")
                
                # Respectful delay between requests
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[Downloader] Exception occurred: {e}")
                time.sleep(5.0)

if __name__ == "__main__":
    import asyncio
    asyncio.run(download_btc_historical_data())
