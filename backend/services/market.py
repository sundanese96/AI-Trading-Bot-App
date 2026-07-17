import random
import time
import httpx
import asyncio
import math
from typing import List, Dict, Any

# Global Simulated State
initial_assets = [
    { "symbol": 'BTC', "name": 'Bitcoin', "price": 62450.00, "change24h": -1.2, "history": [], "type": 'crypto' },
    { "symbol": 'ETH', "name": 'Ethereum', "price": 3420.50, "change24h": -1.8, "history": [], "type": 'crypto' },
    { "symbol": 'SOL', "name": 'Solana', "price": 138.20, "change24h": -3.4, "history": [], "type": 'crypto' },
    { "symbol": 'XRP', "name": 'Ripple', "price": 0.584, "change24h": -2.1, "history": [], "type": 'crypto' },
    { "symbol": 'XAU', "name": 'Gold / Emas', "price": 2345.80, "change24h": 0.4, "history": [], "type": 'metal' },
    { "symbol": 'DXY', "name": 'US Dollar Index', "price": 104.50, "change24h": 0.15, "history": [], "type": 'fiat' },
]

# Initialize 20 historical points for each
for asset in initial_assets:
    val = asset["price"]
    for _ in range(20):
        pct = (random.random() - 0.5) * 0.008
        val = val * (1 + pct)
        asset["history"].append(round(val, 4 if asset["symbol"] == "XRP" else 2))

assets = list(initial_assets)

real_crypto_prices = {
    "BTC": { "price": 62450.00, "change24h": -1.2 },
    "ETH": { "price": 3420.50, "change24h": -1.8 },
    "SOL": { "price": 138.20, "change24h": -3.4 },
    "XRP": { "price": 0.584, "change24h": -2.1 },
}

fng_cache = {
    "value": "55",
    "value_classification": "Neutral",
    "timestamp": str(int(time.time())),
    "time_until_update": "24000"
}

current_panic = {
    "active": False,
    "type": "NONE",
    "title": "",
    "timeLeft": 0
}

def calculate_asset_volatility(history: List[float]) -> Dict[str, float]:
    if not history or len(history) < 2:
        return { "stdDev": 0.0, "pctVolatility": 0.0 }
    mean = sum(history) / len(history)
    variance = sum((val - mean) ** 2 for val in history) / (len(history) - 1)
    std_dev = math.sqrt(variance)
    pct_volatility = (std_dev / mean) * 100
    return {
        "stdDev": round(std_dev, 4),
        "pctVolatility": round(pct_volatility, 3)
    }

def calculate_news_sentiment_index(news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not news_items:
        return { "score": 0, "classification": "NEUTRAL" }
    total_score = 0
    for item in news_items:
        impact = item.get("impact")
        if impact == "CRITICAL":
            total_score -= 100
        elif impact == "NEGATIVE":
            total_score -= 50
        elif impact == "POSITIVE":
            total_score += 50
    score = round(total_score / len(news_items))
    
    classification = "NEUTRAL"
    if score <= -70:
        classification = "EXTREMELY PANIC/NEGATIVE"
    elif score <= -25:
        classification = "FEARFUL/NEGATIVE"
    elif score >= 25:
        classification = "GREEDY/POSITIVE"
        
    return { "score": score, "classification": classification }

async def update_real_crypto_prices():
    symbols = ['BTC', 'ETH', 'SOL', 'XRP']
    async with httpx.AsyncClient(verify=False) as client:
        for sym in symbols:
            try:
                response = await client.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}USDT", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    price = float(data.get("lastPrice", 0))
                    change = float(data.get("priceChangePercent", 0))
                    if price > 0:
                        real_crypto_prices[sym] = {
                            "price": price,
                            "change24h": change
                        }
            except Exception as e:
                print(f"[Binance API] Failed to fetch real price for {sym}: {e}")

async def update_fear_and_greed_index():
    global fng_cache
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get("https://api.alternative.me/fng/?limit=1", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    fng_cache.clear()
                    fng_cache.update(data["data"][0])
                    print(f"[FNG API] Updated index value: {fng_cache['value']} ({fng_cache['value_classification']})")
                    return
    except Exception as e:
        print(f"[FNG API] Failed to fetch real Fear and Greed Index: {e}")
    
    # Fallback fluctuation
    val = int(fng_cache["value"])
    fluctuation = random.randint(-1, 1)
    new_val = max(1, min(99, val + fluctuation))
    classification = "Neutral"
    if new_val < 25:
        classification = "Extreme Fear"
    elif new_val < 45:
        classification = "Fear"
    elif new_val <= 55:
        classification = "Neutral"
    elif new_val < 75:
        classification = "Greed"
    else:
        classification = "Extreme Greed"
    
    fng_cache.clear()
    fng_cache.update({
        "value": str(new_val),
        "value_classification": classification,
        "timestamp": str(int(time.time())),
        "time_until_update": str(max(0, int(fng_cache.get("time_until_update", "24000")) - 60))
    })

async def market_simulation_loop():
    global assets, current_panic
    while True:
        try:
            new_assets = []
            for asset in assets:
                price = asset["price"]
                change24h = asset["change24h"]
                
                # Sync crypto assets with Binance real-time data if not in simulated panic
                if asset["type"] == "crypto":
                    real = real_crypto_prices.get(asset["symbol"])
                    if real:
                        price = real["price"]
                        change24h = real["change24h"]
                
                change_pct = (random.random() - 0.5) * 0.003 # Base noise (0.15% max)
                
                if current_panic["active"]:
                    if current_panic["type"] == "GEOPOLITICS":
                        if asset["symbol"] == "XAU":
                            change_pct += 0.008
                        elif asset["symbol"] == "BTC":
                            change_pct -= 0.009
                        elif asset["symbol"] == "ETH":
                            change_pct -= 0.012
                        elif asset["symbol"] in ["SOL", "XRP"]:
                            change_pct -= 0.016
                        elif asset["symbol"] == "DXY":
                            change_pct += 0.002
                    elif current_panic["type"] == "MACRO":
                        if asset["symbol"] == "DXY":
                            change_pct += 0.012
                        elif asset["symbol"] == "BTC":
                            change_pct -= 0.008
                        elif asset["symbol"] in ["SOL", "XRP"]:
                            change_pct -= 0.014
                        elif asset["symbol"] == "XAU":
                            change_pct -= 0.004
                    
                    price = price * (1 + change_pct)
                else:
                    # If no panic, traditional assets float slightly
                    if asset["type"] != "crypto":
                        price = price * (1 + change_pct)
                
                history = list(asset["history"][1:]) + [round(price, 4 if asset["symbol"] == "XRP" else 2)]
                
                if current_panic["active"] or asset["type"] != "crypto":
                    initial_price = asset["history"][0] if asset["history"] else price
                    change24h = ((price - initial_price) / initial_price) * 100
                
                new_assets.append({
                    **asset,
                    "price": round(price, 4 if asset["symbol"] == "XRP" else 2),
                    "change24h": round(change24h, 2),
                    "history": history
                })
            
            assets.clear()
            assets.extend(new_assets)
            
            if current_panic["active"]:
                current_panic["timeLeft"] -= 1.5
                if current_panic["timeLeft"] <= 0:
                    current_panic = {
                        "active": False,
                        "type": "NONE",
                        "title": "",
                        "timeLeft": 0
                    }
        except Exception as e:
            print(f"[Market Simulation] Error: {e}")
            
        await asyncio.sleep(1.5)

async def real_prices_loop():
    while True:
        await update_real_crypto_prices()
        await asyncio.sleep(15)

async def fear_and_greed_loop():
    while True:
        await update_fear_and_greed_index()
        await asyncio.sleep(300)
