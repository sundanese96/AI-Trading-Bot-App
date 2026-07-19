"""Utility helper functions extracted from main.py."""
import difflib
import asyncio

_llm_lock = None
llm_response_cache = {}

def get_llm_lock():
    global _llm_lock
    if _llm_lock is None:
        _llm_lock = asyncio.Lock()
    return _llm_lock

def get_asset_current_price(symbol: str) -> float:
    from backend.services.market import assets
    clean_sym = symbol.upper().replace("USDT", "")
    for a in assets:
        if a["symbol"].upper() == clean_sym:
            return a["price"]
    return 0.0

def is_headline_relevant(headline: str, source: str) -> bool:
    if source in ["CryptoPanic RSS", "ForexFactory Calendar", "System Indicator"]:
        return True
    hl_lower = headline.lower()
    finance_keywords = [
        'bitcoin', 'crypto', 'sec', 'etf', 'binance', 'coinbase', 'cpi', 'nfp', 'fomc',
        'fed', 'rate', 'inflation', 'gdp', 'economy', 'market', 'stock', 'wall street'
    ]
    geopolitical_keywords = [
        'war', 'strike', 'attack', 'missile', 'military', 'sanction', 'nuclear', 'conflict',
        'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik', 'serangan', 'geopolitical',
        'tariff', 'china', 'russia', 'ukraine', 'iran', 'israel', 'gaza', 'border', 'clash',
        'treaty', 'alliance', 'summit', 'nato', 'defense'
    ]
    if any(k in hl_lower for k in finance_keywords) or any(k in hl_lower for k in geopolitical_keywords):
        return True
    return False

def is_headline_duplicate(new_headline: str, feed: list, threshold: float = 0.8) -> bool:
    new_lower = new_headline.lower()
    for n in feed:
        existing = n.get("headline", "")
        if existing == new_headline:
            return True
        sim = difflib.SequenceMatcher(None, new_lower, existing.lower()).ratio()
        if sim >= threshold:
            return True
    return False

def _calculate_risk_parameters(bot_settings, live_price, decision, strategy):
    lev_val = int(bot_settings.get("leverage", 10))
    sl_pct = float(bot_settings.get("stopLossPct", 1.5)) * float(bot_settings.get("slMultiplier", 1.0))
    tp_pct = float(bot_settings.get("takeProfitPct", 3.0)) * float(bot_settings.get("tpMultiplier", 1.0))
    margin = float(bot_settings.get("allocationPerTrade", 1000.0))
    
    risk_level = bot_settings.get("riskLevel", "MEDIUM")
    if risk_level == "LOW":
        lev_val = min(lev_val, 5)
        sl_pct = min(sl_pct, 1.5)
    elif risk_level == "MEDIUM":
        lev_val = min(lev_val, 20)
        sl_pct = min(sl_pct, 3.0)
    
    if strategy == "HEDGING":
        h_sl_pct, h_tp_pct = sl_pct, tp_pct # Use the capped sl_pct
        return {
            "lev": lev_val, "margin": margin,
            "long_sl": live_price * (1 - h_sl_pct / 100), "long_tp": live_price * (1 + h_tp_pct / 100),
            "short_sl": live_price * (1 + h_sl_pct / 100), "short_tp": live_price * (1 - h_tp_pct / 100),
            "sl_pct_raw": h_sl_pct, "tp_pct_raw": h_tp_pct
        }
    
    sl_price = live_price * (1 - sl_pct / 100) if decision == "LONG" else live_price * (1 + sl_pct / 100)
    tp_price = live_price * (1 + tp_pct / 100) if decision == "LONG" else live_price * (1 - tp_pct / 100)
    return {"lev": lev_val, "margin": margin, "sl_price": sl_price, "tp_price": tp_price, "sl_pct_raw": sl_pct, "tp_pct_raw": tp_pct}
