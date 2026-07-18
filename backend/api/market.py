import time
from fastapi import APIRouter
from backend.services.market import (
    assets, current_panic, fng_cache, calculate_pearson_correlation
)
from backend.core.logger import logger

router = APIRouter()

@router.get("/api/market-data")
async def get_market_data():
    return {
        "assets": assets,
        "panic": current_panic,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }

@router.get("/api/market/correlations")
async def get_market_correlations():
    target_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "SUI", "DOGE"]
    
    histories = {}
    for a in assets:
        sym = a["symbol"].upper()
        if sym in target_symbols:
            histories[sym] = a["history"]
            
    matrix = {}
    for sym_a in target_symbols:
        matrix[sym_a] = {}
        for sym_b in target_symbols:
            if sym_a == sym_b:
                matrix[sym_a][sym_b] = 1.0
            else:
                hist_a = histories.get(sym_a, [])
                hist_b = histories.get(sym_b, [])
                r = calculate_pearson_correlation(hist_a, hist_b)
                matrix[sym_a][sym_b] = round(r, 2)
                
    return {
        "matrix": matrix
    }

@router.get("/api/fear-and-greed")
async def get_fear_and_greed():
    return fng_cache
