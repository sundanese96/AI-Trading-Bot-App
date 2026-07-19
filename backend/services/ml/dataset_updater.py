import asyncio
import httpx
import pandas as pd
from pathlib import Path
import time

DATA_DIR = Path("backend/Train-data")
if not DATA_DIR.exists():
    DATA_DIR = Path("Train-data") # fallback
DATA_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def update_dataset(symbol: str, start_date_str: str, end_date_str: str):
    """
    Downloads and updates the .feather dataset for a specific symbol and date range.
    start_date_str: "YYYY-MM-DD"
    end_date_str: "YYYY-MM-DD"
    """
    feather_path = DATA_DIR / f"{symbol}_5m.feather"
    
    start_ts = int(pd.to_datetime(start_date_str, utc=True).timestamp() * 1000)
    # End date should include the whole day, so add 1 day and subtract 1 ms
    end_ts = int(pd.to_datetime(end_date_str, utc=True).timestamp() * 1000) + 86400000 - 1
    
    # Cap end_ts at current time
    now_ts = int(time.time() * 1000)
    if end_ts > now_ts:
        end_ts = now_ts

    print(f"[{symbol}] Updating dataset from {start_date_str} to {end_date_str}")
    
    existing_df = pd.DataFrame()
    if feather_path.exists():
        try:
            existing_df = pd.read_feather(str(feather_path))
            print(f"[{symbol}] Loaded {len(existing_df)} existing records from {feather_path}")
        except Exception as e:
            print(f"[{symbol}] Error loading existing feather: {e}. Starting fresh.")
    
    new_klines = []
    current_ts = start_ts
    limit = 1500
    backoff_delay = 2.0
    
    # We don't want this to block the server forever, but since this might take a minute,
    # we yield nicely to the event loop.
    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
        while current_ts < end_ts:
            params = {
                "symbol": symbol,
                "interval": "5m", 
                "startTime": current_ts,
                "endTime": end_ts,
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
                    break
                
                for k in data:
                    new_klines.append({
                        "date": pd.to_datetime(k[0], unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                last_kline_ts = int(data[-1][0])
                if last_kline_ts >= end_ts or len(data) < limit:
                    break
                    
                current_ts = last_kline_ts + 300000
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"[{symbol}] Exception during download: {e}")
                await asyncio.sleep(3.0)

    if not new_klines:
        print(f"[{symbol}] No new data found in this range.")
        return {"status": "success", "message": "No new data found", "downloaded": 0, "total": len(existing_df)}

    # Convert new klines to df
    new_df = pd.DataFrame(new_klines)
    
    # Combine and drop duplicates
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        
    # Drop duplicates by date, keeping the last one
    combined_df = combined_df.drop_duplicates(subset=["date"], keep="last")
    
    # Sort by date
    combined_df["date_parsed"] = pd.to_datetime(combined_df["date"])
    combined_df = combined_df.sort_values(by="date_parsed").drop(columns=["date_parsed"]).reset_index(drop=True)
    
    # Save
    combined_df.to_feather(str(feather_path))
    print(f"[{symbol}] Saved {len(combined_df)} total records to {feather_path}")
    
    return {
        "status": "success", 
        "message": f"Successfully updated {symbol} dataset.", 
        "downloaded": len(new_df), 
        "total": len(combined_df)
    }
