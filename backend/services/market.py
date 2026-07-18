import random
import time
import httpx
import asyncio
import math
from typing import List, Dict, Any
from backend.config import VERIFY_SSL
from backend.core.logger import logger

# Global Simulated State
initial_assets = [
    { "symbol": 'BTC', "name": 'Bitcoin', "price": 62450.00, "change24h": -1.2, "history": [], "type": 'crypto' },
    { "symbol": 'ETH', "name": 'Ethereum', "price": 3420.50, "change24h": -1.8, "history": [], "type": 'crypto' },
    { "symbol": 'SOL', "name": 'Solana', "price": 138.20, "change24h": -3.4, "history": [], "type": 'crypto' },
    { "symbol": 'BNB', "name": 'BNB', "price": 580.00, "change24h": -0.5, "history": [], "type": 'crypto' },
    { "symbol": 'XRP', "name": 'Ripple', "price": 0.584, "change24h": -2.1, "history": [], "type": 'crypto' },
    { "symbol": 'ADA', "name": 'Cardano', "price": 0.452, "change24h": -1.5, "history": [], "type": 'crypto' },
    { "symbol": 'SUI', "name": 'Sui', "price": 1.82, "change24h": 2.4, "history": [], "type": 'crypto' },
    { "symbol": 'DOGE', "name": 'Dogecoin', "price": 0.142, "change24h": -4.2, "history": [], "type": 'crypto' },
    { "symbol": 'XAU', "name": 'Gold / Emas', "price": 2345.80, "change24h": 0.4, "history": [], "type": 'metal' },
    { "symbol": 'DXY', "name": 'US Dollar Index', "price": 104.50, "change24h": 0.15, "history": [], "type": 'fiat' },
]

# Initialize 20 historical points for each
for asset in initial_assets:
    val = asset["price"]
    for _ in range(20):
        pct = (random.random() - 0.5) * 0.008
        val = val * (1 + pct)
        asset["history"].append(round(val, 4 if asset["symbol"] in ["XRP", "ADA", "DOGE"] else 2))

assets = list(initial_assets)

real_crypto_prices = {
    "BTC": { "price": 62450.00, "change24h": -1.2 },
    "ETH": { "price": 3420.50, "change24h": -1.8 },
    "SOL": { "price": 138.20, "change24h": -3.4 },
    "BNB": { "price": 580.00, "change24h": -0.5 },
    "XRP": { "price": 0.584, "change24h": -2.1 },
    "ADA": { "price": 0.452, "change24h": -1.5 },
    "SUI": { "price": 1.82, "change24h": 2.4 },
    "DOGE": { "price": 0.142, "change24h": -4.2 },
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
    symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'ADA', 'SUI', 'DOGE']
    async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
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
                logger.error(f"[Binance API] Failed to fetch real price for {sym}: {e}")

async def update_fear_and_greed_index():
    global fng_cache
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            response = await client.get("https://api.alternative.me/fng/?limit=1", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    fng_cache.clear()
                    fng_cache.update(data["data"][0])
                    logger.info(f"[FNG API] Updated index value: {fng_cache['value']} ({fng_cache['value_classification']})")
                    return
    except Exception as e:
        logger.error(f"[FNG API] Failed to fetch real Fear and Greed Index: {e}")
    
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
                        elif asset["symbol"] in ["SOL", "XRP", "BNB", "ADA", "SUI", "DOGE"]:
                            change_pct -= 0.016
                        elif asset["symbol"] == "DXY":
                            change_pct += 0.002
                    elif current_panic["type"] == "MACRO":
                        if asset["symbol"] == "DXY":
                            change_pct += 0.012
                        elif asset["symbol"] == "BTC":
                            change_pct -= 0.008
                        elif asset["symbol"] in ["SOL", "XRP", "BNB", "ADA", "SUI", "DOGE"]:
                            change_pct -= 0.014
                        elif asset["symbol"] == "XAU":
                            change_pct -= 0.004
                    
                    price = price * (1 + change_pct)
                else:
                    # If no panic, traditional assets float slightly
                    if asset["type"] != "crypto":
                        price = price * (1 + change_pct)
                
                is_small_asset = asset["symbol"] in ["XRP", "ADA", "DOGE"]
                history = list(asset["history"][1:]) + [round(price, 4 if is_small_asset else 2)]
                
                if current_panic["active"] or asset["type"] != "crypto":
                    initial_price = asset["history"][0] if asset["history"] else price
                    change24h = ((price - initial_price) / initial_price) * 100
                
                new_assets.append({
                    **asset,
                    "price": round(price, 4 if is_small_asset else 2),
                    "change24h": round(change24h, 2),
                    "history": history
                })
            
            assets[:] = new_assets
            
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
            logger.error(f"[Market Simulation] Error: {e}")
            
        await asyncio.sleep(1.5)

async def real_prices_loop():
    while True:
        await update_real_crypto_prices()
        await asyncio.sleep(15)

async def fear_and_greed_loop():
    while True:
        await update_fear_and_greed_index()
        await asyncio.sleep(300)

def calculate_pearson_correlation(hist_x: List[float], hist_y: List[float]) -> float:
    if len(hist_x) < 3 or len(hist_y) < 3:
        return 0.0
    # Align histories to the same length
    length = min(len(hist_x), len(hist_y))
    x = hist_x[-length:]
    y = hist_y[-length:]
    
    # Calculate returns
    ret_x = [(x[i] - x[i-1]) / x[i-1] for i in range(1, length)]
    ret_y = [(y[i] - y[i-1]) / y[i-1] for i in range(1, length)]
    
    mean_x = sum(ret_x) / len(ret_x)
    mean_y = sum(ret_y) / len(ret_y)
    
    num = sum((ret_x[i] - mean_x) * (ret_y[i] - mean_y) for i in range(len(ret_x)))
    den_x = sum((ret_x[i] - mean_x) ** 2 for i in range(len(ret_x)))
    den_y = sum((ret_y[i] - mean_y) ** 2 for i in range(len(ret_y)))
    
    if den_x == 0 or den_y == 0:
        return 0.0
    
    return num / math.sqrt(den_x * den_y)

def calculate_asset_beta(hist_target: List[float], hist_btc: List[float]) -> Dict[str, float]:
    if len(hist_target) < 3 or len(hist_btc) < 3:
        return { "correlation": 0.0, "beta": 1.0, "stdDevTarget": 0.0, "stdDevBtc": 0.0 }
    
    length = min(len(hist_target), len(hist_btc))
    t = hist_target[-length:]
    b = hist_btc[-length:]
    
    ret_t = [(t[i] - t[i-1]) / t[i-1] for i in range(1, length)]
    ret_b = [(b[i] - b[i-1]) / b[i-1] for i in range(1, length)]
    
    mean_t = sum(ret_t) / len(ret_t)
    mean_b = sum(ret_b) / len(ret_b)
    
    # Variance and Covariance (sample-based, using N-1)
    n = len(ret_t)
    var_b = sum((ret_b[i] - mean_b) ** 2 for i in range(n)) / (n - 1)
    cov_tb = sum((ret_t[i] - mean_t) * (ret_b[i] - mean_b) for i in range(n)) / (n - 1)
    
    if var_b == 0:
        return { "correlation": 0.0, "beta": 1.0, "stdDevTarget": 0.0, "stdDevBtc": 0.0 }
    
    beta = cov_tb / var_b
    
    std_t = math.sqrt(sum((ret_t[i] - mean_t) ** 2 for i in range(n)) / (n - 1))
    std_b = math.sqrt(var_b)
    correlation = 0.0
    if std_t > 0 and std_b > 0:
        correlation = cov_tb / (std_t * std_b)
        
    return {
        "correlation": round(correlation, 4),
        "beta": round(beta, 4),
        "stdDevTarget": round(std_t, 6),
        "stdDevBtc": round(std_b, 6)
    }