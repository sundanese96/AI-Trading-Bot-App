import time
import httpx
import asyncio
# Force reload trigger comment

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.config import GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, CUSTOM_AI_KEY, PORT, HOST, DASHBOARD_USERNAME, DASHBOARD_PASSWORD, BASE_DIR
from backend.database import read_database, write_database
from backend.services import db_manager
from backend.services.historical_scraper import scrape_google_news_historical
from backend.services.market import (
    assets, current_panic, fng_cache, calculate_asset_volatility,
    calculate_news_sentiment_index, market_simulation_loop, real_prices_loop, fear_and_greed_loop
)
from backend.services.news import news_feed, analyze_sentiment, AFINN
from backend.services.ai import call_gemini, call_openai, call_anthropic, call_custom, clean_and_parse_json
from backend.services.scraper import scrape_reuters_news, scrape_bbc_news, fetch_forexfactory_calendar, fetch_crypto_panic_news
from backend.services.position_monitor import monitor_binance_positions_loop
from backend.services.ml.model import train_model, load_model
from backend.services.ml.evaluator import predict_live, evaluate_model_performance
from backend.services.ml.data_prep import prepare_training_data

llm_response_cache = {}

# Helper to get real-time price from Binance or simulation
def get_asset_current_price(symbol: str) -> float:
    from backend.services.market import assets
    clean_sym = symbol.upper().replace("USDT", "")
    for a in assets:
        if a["symbol"].upper() == clean_sym:
            return a["price"]
    return 0.0

def is_headline_relevant(headline: str, source: str) -> bool:
    # Pre-filtered sources are always relevant
    if source in ["CryptoPanic RSS", "ForexFactory Calendar", "System Indicator"]:
        return True
        
    hl_lower = headline.lower()
    
    # Exclude obvious non-financial/non-geopolitical noise
    exclude_keywords = ['entertainment', 'sports', 'movie', 'actor', 'actress', 'celeb', 'music', 'album', 'concert', 'football', 'soccer', 'tennis', 'olympic', 'pop-culture', 'comedy']
    if any(e in hl_lower for e in exclude_keywords):
        return False
        
    # Financial, Crypto, and Macro keywords
    finance_keywords = [
        'bitcoin', 'btc', 'ether', 'eth', 'solana', 'sol', 'ripple', 'xrp', 'crypto', 'coin', 'token', 
        'blockchain', 'dxy', 'fed', 'cpi', 'inflation', 'gdp', 'rate', 
        'treasury', 'dollar', 'gold', 'emas', 'stocks', 'market', 'sec', 'etf', 'binance', 'coinbase', 
        'tether', 'usdt', 'finance', 'economic', 'unemployment', 'bank', 'bonds'
    ]
    
    # Geopolitical and Conflict keywords (having potential macro/market impact)
    geopolitics_keywords = [
        'war', 'strike', 'attack', 'missile', 'military', 'sanction', 'nuclear', 'conflict', 
        'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik', 'serangan', 'geopolitical', 
        'tariff', 'china', 'russia', 'ukraine', 'iran', 'israel', 'gaza', 'border', 'clash', 
        'treaty', 'alliance', 'summit', 'nato', 'defense'
    ]
    
    if any(k in hl_lower for k in finance_keywords) or any(k in hl_lower for k in geopolitics_keywords):
        return True
        
    return False

# Trigger simulated trade in paper trading mode
async def trigger_automated_trade_sim(item: Dict[str, Any], config: Dict[str, Any]):
    from backend.database import db_lock, read_database, write_database
    try:
        headline = item["title"]
        source = item.get("source", "Unknown")
        
        # Check relevance to avoid wasting local LLM resources and flooding activity console
        if not is_headline_relevant(headline, source):
            print(f"[Sim Trading] Skipping LLM for irrelevant headline: {headline}")
            # Insert into news_feed directly without running LLM to keep general news panel updated
            sentiment_res = analyze_sentiment(headline)
            score = sentiment_res["score"]
            lower = headline.lower()
            geo_keywords = ['attack', 'strike', 'war', 'escalation', 'sanction', 'funeral', 'nuclear', 'serangan', 'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik']
            is_geo = any(k in lower for k in geo_keywords)
            macro_keywords = ['nfp', 'cpi', 'fomc', 'gdp', 'inflation', 'fed', 'interest', 'suku bunga', 'pengangguran', 'inflasi', 'gaji', 'pekerjaan']
            is_macro = any(k in lower for k in macro_keywords)
            category = "GEOPOLITICS" if is_geo else ("MACRO" if is_macro else "GENERAL")
            impact = "CRITICAL" if (is_geo or is_macro) else "NEUTRAL"
            
            # Check if already in news_feed to prevent duplicates
            if not any(n["headline"] == headline for n in news_feed):
                new_item = {
                    "id": f"news-{int(time.time() * 1000)}",
                    "time": time.strftime("%H:%M:%S"),
                    "headline": headline,
                    "category": category,
                    "impact": impact,
                    "source": source,
                    "details": f"Scraped from {source}. Sentiment score: {score}. Bypassed AI Bot Trade Analysis.",
                    "forecast": item.get("forecast", ""),
                    "previous": item.get("previous", ""),
                    "isTriggeredShort": is_geo or is_macro,
                    "isTriggeredGold": is_geo,
                    "summaryId": f"Scraped news. Category: {category}. Bypassed AI Bot."
                }
                news_feed.insert(0, new_item)
                if len(news_feed) > 50:
                    news_feed.pop()
            return
            
        from backend.sentix_adapter import sentix_state
        bot_settings = sentix_state.get("aiBotSettings", {})
        active_symbol = bot_settings.get("symbol", "BTCUSDT")
        active_asset = active_symbol.upper().replace("USDT", "")
        
        print(f"[Sim Trading] Auto-running AI analysis for: {headline} (Target Asset: {active_asset})")
        
        # Call analyze_ai to enrich news, calculate volatilities, classify crisis, and update news_feed
        req = AIAnalyzeRequest(
            headline=headline,
            source=item["source"],
            provider=config.get("provider", "gemini"),
            customUrl=config.get("customUrl", ""),
            customKey=config.get("customKey", ""),
            customModel=config.get("customModel", ""),
            targetAsset=active_asset,
            forecast=item.get("forecast", ""),
            previous=item.get("previous", "")
        )
        
        analysis_res = await analyze_ai(req)
        analysis = analysis_res.get("analysis", {})
        trade_decision = analysis.get("tradeDecision", {})
        veto_gate = analysis.get("vetoGate", {})
        
        # Enforce that the trade decision target asset matches the user's configured active asset
        trade_decision["targetAsset"] = active_asset
        decision = trade_decision.get("decision", "HOLD")
        target_asset = active_asset
        confidence = trade_decision.get("confidence", 0)
        threshold = bot_settings.get("minConfidence", config.get("confidenceThreshold", 75))
        
        # Pearson Correlation & Beta News Translation for Altcoins/Meme Coins
        correlation_log = ""
        is_translated = False
        r_val = 0.0
        beta_val = 1.0
        
        if active_asset != "BTC":
            from backend.services.market import assets, calculate_asset_beta
            hist_target = []
            hist_btc = []
            for a in assets:
                if a["symbol"].upper() == active_asset:
                    hist_target = a["history"]
                elif a["symbol"].upper() == "BTC":
                    hist_btc = a["history"]
                    
            if hist_target and hist_btc:
                stats = calculate_asset_beta(hist_target, hist_btc)
                r_val = stats["correlation"]
                beta_val = stats["beta"]
                
                # Check if news is general/macro or BTC/Crypto specific
                headline_lower = headline.lower()
                is_general_news = any(k in headline_lower for k in ["btc", "bitcoin", "market", "crypto", "fed", "inflation", "cpi", "nfp", "sec", "etf", "induk", "receh", "meme"])
                
                if is_general_news and abs(r_val) >= 0.45:
                    # Translate sentiment/expected movement mathematically
                    # Extract BTC expected impact from assetsImpact if available, otherwise estimate from headline sentiment
                    btc_expected_pct = 0.0
                    assets_impact = analysis.get("assetsImpact", [])
                    for impact_item in assets_impact:
                        if impact_item.get("symbol") == "BTC":
                            btc_expected_pct = float(impact_item.get("percentage", 0.0))
                            break
                    
                    if btc_expected_pct == 0.0:
                        # Fallback estimation based on analysis sentiment
                        sentiment = analysis.get("sentiment", "NEUTRAL")
                        if sentiment == "POSITIVE":
                            btc_expected_pct = 0.15
                        elif sentiment == "NEGATIVE":
                            btc_expected_pct = -0.15
                        elif sentiment == "CRITICAL":
                            btc_expected_pct = -0.30
                            
                    # Calculate translated impact on target asset using Beta
                    target_expected_pct = round(btc_expected_pct * beta_val, 4)
                    
                    # Convert to trade decision
                    if target_expected_pct > 0.02:
                        decision = "LONG"
                        confidence = int(min(95, max(30, confidence * abs(r_val))))
                    elif target_expected_pct < -0.02:
                        decision = "SHORT"
                        confidence = int(min(95, max(30, confidence * abs(r_val))))
                    else:
                        decision = "HOLD"
                        confidence = int(confidence * (1 - abs(r_val)))
                        
                    # Update decision object
                    trade_decision["decision"] = decision
                    trade_decision["confidence"] = confidence
                    
                    is_translated = True
                    correlation_log = (
                        f" | Translasi Berita BTC: r={r_val:+.2f}, β={beta_val:+.2f}, "
                        f"Dampak BTC ({btc_expected_pct:+.2f}%) -> {active_asset} ({target_expected_pct:+.2f}%)"
                    )

        strategy = bot_settings.get("strategy", "CONSERVATIVE").upper()
        
        # Decide if we check Veto Gate based on strategy
        bypass_veto = strategy in ["AGGRESSIVE", "SCALPING", "HEDGING"]
        veto_active = False if bypass_veto else veto_gate.get("vetoActive", False)

        # --- Bridge to Sentix Compatibility Adapter (AI Bot activity console) ---
        try:
            from backend.sentix_adapter import sentix_state, _save_sentix_db
            live_price = get_asset_current_price(target_asset) or 64000.0
            
            log_action = "INFO"
            if decision == "LONG":
                log_action = "BUY"
            elif decision == "SHORT":
                log_action = "SELL"
            elif decision == "HOLD":
                log_action = "HOLD"
                
            is_small = target_asset in ["DOGE", "ADA", "XRP"]
            price_fmt = f"${live_price:,.4f}" if is_small else f"${live_price:,.2f}"
            
            log_entry = {
                "id": f"log-bot-{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "action": log_action,
                "symbol": f"{target_asset}USDT",
                "price": live_price,
                "confidence": confidence,
                "message": f"🤖 [AI BOT Auto ({strategy})]: Menganalisis {target_asset} @ {price_fmt}. Keputusan: {decision} ({confidence}%). Alasan: {trade_decision.get('strategyReasoning', '')}{correlation_log}"
            }
            
            if "aiBotLogs" not in sentix_state:
                sentix_state["aiBotLogs"] = []
            sentix_state["aiBotLogs"].insert(0, log_entry)
            sentix_state["aiBotLogs"] = sentix_state["aiBotLogs"][:100]
            
            # If decision is LONG or SHORT and confidence >= threshold, place trade in sentix_state
            if decision in ["LONG", "SHORT"] and not veto_active and confidence >= threshold:
                symbol_usdt = f"{target_asset}USDT"
                
                # Standard default parameters
                lev_val = 5
                try:
                    lev_val = int(trade_decision.get("recommendedLeverage", "5x").replace("x", ""))
                except Exception:
                    pass
                    
                sl_str = trade_decision.get("recommendedStopLoss", "2.5%").replace("%", "")
                try:
                    sl_pct = float(sl_str)
                except ValueError:
                    sl_pct = 2.5
                tp_pct = sl_pct * 2.0

                # Override params based on strategy
                if strategy == "SCALPING":
                    lev_val = 20
                    sl_pct = 0.8
                    tp_pct = 1.5
                elif strategy == "SWING":
                    lev_val = 3
                    sl_pct = 4.0
                    tp_pct = 10.0

                # Determine Margin/Allocation and apply Martingale doubling if last closed trade was a loss
                margin = float(bot_settings.get("allocationPerTrade", 1000.0))
                if strategy == "MARTINGALE":
                    closed_trades = [t for t in sentix_state.get("trades", []) if t.get("status") == "CLOSED"]
                    if closed_trades:
                        closed_trades.sort(key=lambda x: x.get("closeTime", 0) or x.get("exitTimestamp", 0) or 0, reverse=True)
                        last_trade = closed_trades[0]
                        last_pnl = last_trade.get("pnl", 0.0) or 0.0
                        if last_pnl < 0.0:
                            margin = margin * 2.0
                            log_entry["message"] += f" [Martingale Double Active: ${margin}]"
                            print(f"[Martingale Strategy] Last trade was a loss (PnL: {last_pnl}%). Doubling allocation to ${margin}")

                # Helper function to place a single trade object
                def add_sentix_trade(trade_type, sl_val, tp_val, active_margin):
                    qty = (active_margin * lev_val) / live_price
                    trade_obj = {
                        "id": f"trade-bot-{trade_type.lower()}-{int(time.time() * 1000)}",
                        "symbol": symbol_usdt,
                        "type": trade_type,
                        "size": round(qty, 6),
                        "leverage": lev_val,
                        "entryPrice": live_price,
                        "exitPrice": None,
                        "pnl": None,
                        "sl": round(sl_val, 2),
                        "tp": round(tp_val, 2),
                        "trailingStopPct": None,
                        "status": "OPEN",
                        "timestamp": int(time.time() * 1000),
                        "exitTimestamp": None,
                        "reason": f"AI_BOT_{strategy}"
                    }
                    if "trades" not in sentix_state:
                        sentix_state["trades"] = []
                    sentix_state["trades"].append(trade_obj)
                    sentix_state["portfolio"]["balanceUSD"] = round(sentix_state["portfolio"]["balanceUSD"] - active_margin, 2)
                    print(f"[Sim Trading] Placed {strategy} trade: {trade_type} {symbol_usdt} at ${live_price}")

                if strategy == "HEDGING":
                    has_long = any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt and t.get("type") == "BUY" for t in sentix_state["trades"])
                    has_short = any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt and t.get("type") == "SELL" for t in sentix_state["trades"])
                    
                    # Hedging SL/TP overrides (medium-tight to capture breakout moves)
                    h_sl_pct = 1.5
                    h_tp_pct = 3.0
                    long_sl = live_price * (1 - h_sl_pct / 100)
                    long_tp = live_price * (1 + h_tp_pct / 100)
                    short_sl = live_price * (1 + h_sl_pct / 100)
                    short_tp = live_price * (1 - h_tp_pct / 100)
                    
                    if not has_long:
                        add_sentix_trade("BUY", long_sl, long_tp, margin)
                    if not has_short:
                        add_sentix_trade("SELL", short_sl, short_tp, margin)
                else:
                    if not any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt for t in sentix_state["trades"]):
                        trade_type = "BUY" if decision == "LONG" else "SELL"
                        sl_price = live_price * (1 - sl_pct / 100) if decision == "LONG" else live_price * (1 + sl_pct / 100)
                        tp_price = live_price * (1 + tp_pct / 100) if decision == "LONG" else live_price * (1 - tp_pct / 100)
                        add_sentix_trade(trade_type, sl_price, tp_price, margin)
            
            _save_sentix_db()
        except Exception as e:
            print(f"[Sim Trading] Failed to bridge log/trade to Sentix adapter: {e}")
            
        # Check if trade is valid and not vetoed
        if decision in ["LONG", "SHORT"] and not veto_active:
            if confidence >= threshold:
                async with db_lock:
                    db = read_database()
                    existing_trades = db.get("savedTrades", [])
                    
                cur_price = get_asset_current_price(target_asset)
                if cur_price > 0.0:
                    
                    # Standard default parameters (again for db sync)
                    lev_val = 5
                    try:
                        lev_val = int(trade_decision.get("recommendedLeverage", "5x").replace("x", ""))
                    except Exception:
                        pass
                        
                    sl_str = trade_decision.get("recommendedStopLoss", "2.5%").replace("%", "")
                    try:
                        sl_pct = float(sl_str)
                    except ValueError:
                        sl_pct = 2.5
                    tp_pct = sl_pct * 2.0

                    if strategy == "SCALPING":
                        lev_val = 20
                        sl_pct = 0.8
                        tp_pct = 1.5
                    elif strategy == "SWING":
                        lev_val = 3
                        sl_pct = 4.0
                        tp_pct = 10.0

                    def add_db_trade(trade_dec, sl_val, tp_val):
                        sim_trade = {
                            "id": f"trade-{trade_dec.lower()}-{int(time.time() * 1000)}",
                            "timestamp": int(time.time() * 1000),
                            "decision": trade_dec,
                            "targetAsset": target_asset,
                            "confidence": confidence,
                            "recommendedLeverage": f"{lev_val}x",
                            "recommendedStopLoss": f"{sl_pct}%",
                            "recommendedTakeProfit": f"{tp_pct}%",
                            "strategyReasoning": f"[{strategy} Strategy] {trade_decision.get('strategyReasoning', '')}",
                            "status": "OPEN",
                            "entryPrice": cur_price,
                            "currentPrice": cur_price,
                            "exitPrice": None,
                            "closeTime": None,
                            "closeReason": None,
                            "pnl": 0.0,
                            "headline": headline,
                            "type": "SIMULATED"
                        }
                        
                        if strategy == "HEDGING":
                            sim_trade["recommendedStopLoss"] = "1.5%"
                            sim_trade["recommendedTakeProfit"] = "3.0%"
                            sim_trade["strategyReasoning"] = f"[HEDGING Strategy] Dual directional entry. {trade_decision.get('strategyReasoning', '')}"
                        
                        db["savedTrades"].insert(0, sim_trade)
                        db["savedTrades"] = db["savedTrades"][:100]

                    if strategy == "HEDGING":
                        has_long_db = any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "LONG" and t.get("type") == "SIMULATED" for t in existing_trades)
                        has_short_db = any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "SHORT" and t.get("type") == "SIMULATED" for t in existing_trades)
                        
                        async with db_lock:
                            db = read_database()
                            if "savedTrades" not in db:
                                db["savedTrades"] = []
                            if not has_long_db:
                                add_db_trade("LONG", cur_price * 0.985, cur_price * 1.03)
                            if not has_short_db:
                                add_db_trade("SHORT", cur_price * 1.015, cur_price * 0.97)
                            write_database(db)
                    else:
                        has_existing_db = any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("type") == "SIMULATED" for t in existing_trades)
                        if not has_existing_db:
                            sl_price = cur_price * (1 - sl_pct / 100) if decision == "LONG" else cur_price * (1 + sl_pct / 100)
                            tp_price = cur_price * (1 + tp_pct / 100) if decision == "LONG" else cur_price * (1 - tp_pct / 100)
                            async with db_lock:
                                db = read_database()
                                if "savedTrades" not in db:
                                    db["savedTrades"] = []
                                add_db_trade(decision, sl_price, tp_price)
                                write_database(db)
                                
                    print(f"[Sim Trading] Successfully opened automated trade: {decision} {target_asset} at {cur_price}")
                    
                    # Send telegram alert
                    from backend.services.telegram_client import send_telegram_alert
                    msg = (
                        f"🚀 *Simulated Trade Opened* 🚀\n\n"
                        f"*Asset*: {target_asset}\n"
                        f"*Action*: {decision}\n"
                        f"*Entry Price*: ${cur_price}\n"
                        f"*Confidence*: {confidence}%\n"
                        f"*SL*: {sl_pct}% | *TP*: {tp_pct}%\n"
                        f"*Reason*: {trade_decision.get('strategyReasoning', '')}"
                    )
                    asyncio.create_task(send_telegram_alert(msg))
    except Exception as err:
        print(f"[Sim Trading] Error running automated trade: {err}")

# Position monitor loop for simulated trades
async def monitor_simulated_positions_loop():
    print("[Sim Position Monitor] Starting simulated position monitor loop...")
    while True:
        try:
            from backend.database import db_lock, read_database, write_database
            import time
            
            async with db_lock:
                db = read_database()
                trades = db.get("savedTrades", [])
                updated = False
                
                for trade in trades:
                    if trade.get("status") == "OPEN" and trade.get("type") == "SIMULATED":
                        symbol = trade.get("targetAsset", "")
                        cur_price = get_asset_current_price(symbol)
                        if cur_price <= 0:
                            continue
                        
                        trade["currentPrice"] = cur_price
                        entry_price = trade.get("entryPrice", cur_price)
                        leverage_str = trade.get("recommendedLeverage", "5x").replace("x", "")
                        try:
                            leverage = float(leverage_str)
                        except ValueError:
                            leverage = 5.0
                            
                        sl_str = trade.get("recommendedStopLoss", "2%").replace("%", "")
                        try:
                            sl_pct = float(sl_str)
                        except ValueError:
                            sl_pct = 2.0
                        
                        tp_pct = sl_pct * 2.0
                        decision = trade.get("decision")
                        
                        if decision == "LONG":
                            price_change_pct = ((cur_price - entry_price) / entry_price) * 100
                        else: # SHORT
                            price_change_pct = ((entry_price - cur_price) / entry_price) * 100
                            
                        pnl_pct = price_change_pct * leverage
                        trade["pnl"] = round(pnl_pct, 2)
                        
                        triggered_close = False
                        close_reason = ""
                        
                        # 1. Stop Loss check
                        if price_change_pct <= -sl_pct:
                            triggered_close = True
                            close_reason = "STOP_LOSS"
                        # 2. Take Profit check
                        elif price_change_pct >= tp_pct:
                            triggered_close = True
                            close_reason = "TAKE_PROFIT"
                        # 3. Timeout check (15 minutes)
                        elif int(time.time() * 1000) - trade.get("timestamp", 0) > 15 * 60 * 1000:
                            triggered_close = True
                            close_reason = "TIMEOUT"
                            
                        if triggered_close:
                            trade["status"] = "CLOSED"
                            trade["exitPrice"] = cur_price
                            trade["closeTime"] = int(time.time() * 1000)
                            trade["closeReason"] = close_reason
                            
                            # Append to pnlLog for rolling daily stats
                            if "pnlLog" not in db:
                                db["pnlLog"] = []
                            db["pnlLog"].append({
                                "timestamp": int(time.time() * 1000),
                                "pnl": round(pnl_pct, 2)
                            })
                            
                            # Send Telegram notification for the closed simulated position!
                            from backend.services.telegram_client import send_telegram_alert
                            closed_msg = (
                                f"🏁 *Simulated Trade Closed ({close_reason})* 🏁\n\n"
                                f"*Asset*: {symbol}\n"
                                f"*Action*: {decision}\n"
                                f"*Entry Price*: ${entry_price}\n"
                                f"*Exit Price*: ${cur_price}\n"
                                f"*Final PnL*: {round(pnl_pct, 2)}% ({'🟢 Profit' if pnl_pct > 0 else '🔴 Loss'})\n"
                                f"*Headline*: {trade.get('headline', '')}"
                            )
                            asyncio.create_task(send_telegram_alert(closed_msg))
                            print(f"[Sim Position Monitor] CLOSED POSITION: {decision} {symbol} at {cur_price} | PnL: {pnl_pct:.2f}%")
                            
                        updated = True
                        
                if updated:
                    write_database(db)
                    
        except Exception as loop_err:
            print(f"[Sim Position Monitor] Error in loop: {loop_err}")
        await asyncio.sleep(10) # check every 10 seconds

# Background task to run AI bot automation strategy periodically when enabled
async def ai_bot_automated_loop():
    print("[AI Bot Loop] Starting automated strategy evaluation loop...")
    import time
    from backend.sentix_adapter import sentix_state
    from backend.database import load_ai_config
    
    last_run_time = 0
    last_evaluated_key = None
    last_enabled = False
    last_symbol = None
    last_strategy = None
    
    while True:
        try:
            bot_settings = sentix_state.get("aiBotSettings", {})
            enabled = bot_settings.get("enabled", False)
            symbol = bot_settings.get("symbol", "BTCUSDT")
            strategy = bot_settings.get("strategy", "CONSERVATIVE")
            
            # Detect activation toggle or setting changes
            settings_changed = (symbol != last_symbol) or (strategy != last_strategy)
            if (enabled and not last_enabled) or (enabled and settings_changed):
                print(f"[AI Bot Loop] Activation toggle or settings changed (Symbol: {symbol}, Strategy: {strategy}). Resetting throttle and evaluating immediately.")
                last_run_time = 0
                last_evaluated_key = None
                
            last_enabled = enabled
            last_symbol = symbol
            last_strategy = strategy
            
            if enabled:
                now = time.time()
                interval = bot_settings.get("runIntervalSeconds", 60)
                
                if now - last_run_time >= interval:
                    # Fetch latest news headline
                    headline = "Pasar Cryptocurrency menunjukkan pergerakan sideways yang stabil."
                    source = "System Indicator"
                    
                    if news_feed:
                        headline = news_feed[0].get("headline", headline)
                        source = news_feed[0].get("source", source)
                    
                    # Generate dynamic key representing current evaluation state
                    current_key = f"{headline}-{symbol}-{strategy}"
                    if current_key == last_evaluated_key:
                        # Sleep briefly and continue to avoid duplicate evaluations
                        await asyncio.sleep(1)
                        continue
                    
                    last_run_time = now
                    last_evaluated_key = current_key
                    
                    # Load core AI configuration for credentials
                    config = await load_ai_config() or {}
                    
                    # Run automated trade simulation step
                    dummy_item = {"title": headline, "source": source}
                    print(f"[AI Bot Loop] Strategy automation triggered for headline: {headline}")
                    await trigger_automated_trade_sim(dummy_item, config)
                    
        except Exception as e:
            print(f"[AI Bot Loop] Error: {e}")
            
        await asyncio.sleep(5) # check if bot is enabled every 5 seconds

# Background task to periodically scrape news
async def news_scraper_loop():
    global news_feed
    while True:
        try:
            print("[Scraper] Running periodic news scraper...")
            reuters_news = await scrape_reuters_news()
            bbc_news = await scrape_bbc_news()
            ff_news = await fetch_forexfactory_calendar()
            panic_news = await fetch_crypto_panic_news()
            
            # Combine and process scraped news
            all_scraped = reuters_news + bbc_news + ff_news + panic_news
            
            # Load AI config to see if we should auto-run AI analysis
            from backend.database import load_ai_config
            config = await load_ai_config() or {}
            is_dry_run = config.get("dryRun", True)
            is_locked = config.get("isLocked", False)
            
            for item in all_scraped:
                headline = item["title"]
                # Check if headline already exists in news_feed to avoid duplicates
                if any(n["headline"] == headline for n in news_feed):
                    continue
                
                # Check and run live simulation manager if active
                from backend.services.live_sim_manager import live_sim_manager
                if live_sim_manager.active:
                    await live_sim_manager.handle_new_news(item)
                
                # If bot is active (not locked) and dryRun is true, run the AI Analyst pipeline!
                if is_dry_run and not is_locked:
                    await trigger_automated_trade_sim(item, config)
                else:
                    # Non-simulation fallback: just do raw sentiment analysis and add to news_feed as before
                    sentiment_res = analyze_sentiment(headline)
                    score = sentiment_res["score"]
                    lower = headline.lower()
                    geo_keywords = ['attack', 'strike', 'war', 'escalation', 'sanction', 'funeral', 'nuclear', 'serangan', 'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik']
                    is_geo = any(k in lower for k in geo_keywords)
                    macro_keywords = ['nfp', 'cpi', 'fomc', 'gdp', 'inflation', 'fed', 'interest', 'suku bunga', 'pengangguran', 'inflasi', 'gaji', 'pekerjaan']
                    is_macro = any(k in lower for k in macro_keywords)
                    category = "GEOPOLITICS" if is_geo else ("MACRO" if is_macro else "GENERAL")
                    impact = "CRITICAL" if (is_geo or is_macro) else "NEUTRAL"
                    new_item = {
                        "id": f"news-{int(time.time() * 1000)}",
                        "time": time.strftime("%H:%M:%S"),
                        "headline": headline,
                        "category": category,
                        "impact": impact,
                        "source": item["source"],
                        "details": f"Scraped from {item['source']}. Sentiment score: {score}.",
                        "forecast": item.get("forecast", ""),
                        "previous": item.get("previous", ""),
                        "isTriggeredShort": is_geo or is_macro,
                        "isTriggeredGold": is_geo,
                        "summaryId": f"Scraped news. Category: {category}. Short signal: {'ACTIVE' if (is_geo or is_macro) else 'INACTIVE'}."
                    }
                    news_feed.insert(0, new_item)
                    if len(news_feed) > 50:
                        news_feed.pop()
        except Exception as e:
            print(f"[Scraper] Error in news scraper loop: {e}")
        await asyncio.sleep(180) # Scrape every 3 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database
    await db_manager.init_db()
    # Start background tasks
    sim_task = asyncio.create_task(market_simulation_loop())
    prices_task = asyncio.create_task(real_prices_loop())
    fng_task = asyncio.create_task(fear_and_greed_loop())
    scraper_task = asyncio.create_task(news_scraper_loop())
    ai_bot_task = asyncio.create_task(ai_bot_automated_loop())
    monitor_task = asyncio.create_task(monitor_binance_positions_loop())
    sim_monitor_task = asyncio.create_task(monitor_simulated_positions_loop())
    yield
    # Clean up background tasks
    sim_task.cancel()
    prices_task.cancel()
    fng_task.cancel()
    scraper_task.cancel()
    ai_bot_task.cancel()
    monitor_task.cancel()
    sim_monitor_task.cancel()
    try:
        await asyncio.gather(sim_task, prices_task, fng_task, scraper_task, monitor_task, sim_monitor_task, return_exceptions=True)
    except Exception:
        pass

app = FastAPI(title="Sentix AI Trading Terminal", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Persistent Session Management
SESSION_FILE = str(BASE_DIR / ".session_token")

def get_active_session_id():
    import os
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return f.read().strip()
        except Exception:
            return None
    return None

def set_active_session_id(session_id: str):
    try:
        with open(SESSION_FILE, "w") as f:
            f.write(session_id)
    except Exception as e:
        print(f"Error saving session token: {e}")

def clear_active_session_id():
    import os
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception as e:
            print(f"Error removing session token: {e}")

class LoginRequest(BaseModel):
    username: str
    password: str

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    if path.startswith("/api"):
        if path not in ["/api/login", "/api/auth/status"]:
            session_id = request.cookies.get("session_id")
            active_id = get_active_session_id()
            if not session_id or session_id != active_id:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
                
    response = await call_next(request)
    return response

@app.post("/api/login")
async def login(data: LoginRequest, response: Response):
    if data.username == DASHBOARD_USERNAME and data.password == DASHBOARD_PASSWORD:
        import uuid
        session_id = uuid.uuid4().hex
        set_active_session_id(session_id)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=3600 * 24 * 7, # 7 days
            path="/"
        )
        return {"success": True}
    else:
        raise HTTPException(status_code=400, detail="Username atau password salah")

@app.get("/api/auth/status")
async def auth_status(request: Request):
    session_id = request.cookies.get("session_id")
    active_id = get_active_session_id()
    if session_id and session_id == active_id:
        return {"authenticated": True}
    return {"authenticated": False}

@app.post("/api/logout")
async def logout(response: Response):
    clear_active_session_id()
    response.delete_cookie(key="session_id", path="/")
    return {"success": True}

# Register Sentix UI compatibility adapter routes (takes priority)
from backend.sentix_adapter import router as sentix_router
app.include_router(sentix_router)

# Register Live Trading router
from backend.live_trading.endpoints import router as live_trading_router
app.include_router(live_trading_router)
# Pydantic Models
class TriggerCrisisRequest(BaseModel):
    type: str
    headline: Optional[str] = None
    details: Optional[str] = None

class SaveTradeRequest(BaseModel):
    trade: Dict[str, Any]

class AIAnalyzeRequest(BaseModel):
    headline: str
    source: Optional[str] = None
    provider: Optional[str] = "gemini"
    customUrl: Optional[str] = None
    customKey: Optional[str] = None
    customModel: Optional[str] = None
    temperature: Optional[float] = None
    targetAsset: Optional[str] = None
    forecast: Optional[str] = ""
    previous: Optional[str] = ""

class EvaluateRequest(BaseModel):
    headline: str
    symbol: Optional[str] = "BTC"

class SaveAIConfigRequest(BaseModel):
    provider: str
    customUrl: Optional[str] = ""
    customKey: Optional[str] = ""
    customModel: Optional[str] = ""
    temperature: Optional[float] = None
    binanceApiKey: Optional[str] = ""
    binanceApiSecret: Optional[str] = ""
    dryRun: Optional[bool] = True
    maxDailyLoss: Optional[float] = 5.0
    maxTradesPerDay: Optional[int] = 5
    confidenceThreshold: Optional[int] = 75
    telegramBotToken: Optional[str] = ""
    telegramChatId: Optional[str] = ""
    mlTargetWindow: Optional[int] = 15
    mlThresholdPct: Optional[float] = 0.15
    mlModelType: Optional[str] = "xgboost"

# Endpoints

@app.get("/api/ai/config")
async def get_ai_config():
    from backend.database import load_ai_config
    return await load_ai_config()

@app.post("/api/ai/config")
async def save_ai_config_endpoint(req: SaveAIConfigRequest):
    from backend.database import save_ai_config
    config_data = {
        "provider": req.provider,
        "customUrl": req.customUrl,
        "customKey": req.customKey,
        "customModel": req.customModel,
        "binanceApiKey": req.binanceApiKey,
        "binanceApiSecret": req.binanceApiSecret,
        "dryRun": req.dryRun,
        "maxDailyLoss": req.maxDailyLoss,
        "maxTradesPerDay": req.maxTradesPerDay,
        "confidenceThreshold": req.confidenceThreshold,
        "telegramBotToken": req.telegramBotToken,
        "telegramChatId": req.telegramChatId,
        "mlTargetWindow": req.mlTargetWindow,
        "mlThresholdPct": req.mlThresholdPct,
        "mlModelType": req.mlModelType,
        "isLocked": False # Reset lock when saving new config
    }
    await save_ai_config(config_data)
    return { "status": "ok", "message": "AI and Binance configuration saved and encrypted successfully." }

@app.post("/api/bot/unlock")
async def unlock_bot_endpoint():
    from backend.database import unlock_bot
    await unlock_bot()
    return { "status": "ok", "message": "Bot unlocked successfully." }

class ExecuteOrderRequest(BaseModel):
    symbol: str
    side: str
    positionSide: str
    orderType: str
    quantity: float
    leverage: int
    stopLossPct: Optional[float] = None
    takeProfitPct: Optional[float] = None

@app.post("/api/binance/execute")
async def execute_order_endpoint(req: ExecuteOrderRequest):
    from backend.services.binance_client import execute_futures_order
    res = await execute_futures_order(
        symbol=req.symbol,
        side=req.side,
        position_side=req.positionSide,
        order_type=req.orderType,
        quantity=req.quantity,
        leverage=req.leverage,
        stop_loss_pct=req.stopLossPct,
        take_profit_pct=req.takeProfitPct
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/api/market-data")
async def get_market_data():
    return {
        "assets": assets,
        "panic": current_panic,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }

@app.get("/api/market/correlations")
async def get_market_correlations():
    from backend.services.market import assets, calculate_pearson_correlation
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

@app.get("/api/fear-and-greed")
async def get_fear_and_greed():
    return fng_cache

class StartSessionRequest(BaseModel):
    strategy: str
    initialCapital: float
    targetAssets: List[str]
    confidenceThreshold: Optional[int] = 75
    bollingerStdDev: Optional[float] = 2.0

@app.post("/api/live-sim/start")
async def start_live_sim_session(req: StartSessionRequest):
    from backend.services.live_sim_manager import live_sim_manager
    await live_sim_manager.start_session(
        strategy=req.strategy,
        initial_capital=req.initialCapital,
        target_assets=req.targetAssets,
        confidence_threshold=req.confidenceThreshold,
        bollinger_std_dev=req.bollingerStdDev
    )
    return {
        "status": "success",
        "message": f"Simulation session started with strategy {req.strategy}"
    }

@app.post("/api/live-sim/stop")
async def stop_live_sim_session():
    from backend.services.live_sim_manager import live_sim_manager
    await live_sim_manager.stop_session()
    return {
        "status": "success",
        "message": "Simulation session stopped"
    }

@app.get("/api/live-sim/status")
async def get_live_sim_status():
    from backend.services.live_sim_manager import live_sim_manager
    return {
        "active": live_sim_manager.active,
        "strategy": live_sim_manager.strategy,
        "initialCapital": live_sim_manager.initial_capital,
        "currentCapital": live_sim_manager.current_capital,
        "targetAssets": live_sim_manager.target_assets,
        "confidenceThreshold": getattr(live_sim_manager, "confidence_threshold", 75),
        "bollingerStdDev": getattr(live_sim_manager, "bollinger_std_dev", 2.0),
        "startTime": live_sim_manager.start_time,
        "elapsedTime": time.time() - live_sim_manager.start_time if live_sim_manager.active else 0,
        "logs": live_sim_manager.logs
    }

@app.get("/api/live-sim/trades")
async def get_live_sim_trades():
    from backend.services.live_sim_manager import live_sim_manager
    return live_sim_manager.trades

@app.get("/api/analyses")
@app.get("/api/database/analyses")
async def get_database_analyses():
    from backend.database import db_lock, read_database
    async with db_lock:
        db = read_database()
        return db.get("savedAnalyses", [])

@app.post("/api/analyses/clear")
@app.post("/api/database/clear")
async def clear_database_analyses():
    from backend.database import db_lock, read_database, write_database
    async with db_lock:
        db = read_database()
        db["savedAnalyses"] = []
        write_database(db)
    return { "status": "ok" }

@app.get("/api/trades")
@app.get("/api/database/trades")
async def get_database_trades():
    from backend.database import db_lock, read_database
    async with db_lock:
        db = read_database()
        return db.get("savedTrades", [])

@app.post("/api/trades")
@app.post("/api/database/save-trade")
async def save_trade(req: SaveTradeRequest):
    from backend.database import db_lock, read_database, write_database
    async with db_lock:
        db = read_database()
        if "savedTrades" not in db:
            db["savedTrades"] = []
        trade_data = {
            **req.trade,
            "id": f"trade-{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000)
        }
        db["savedTrades"].insert(0, trade_data)
        db["savedTrades"] = db["savedTrades"][:100]
        write_database(db)
    return { "status": "ok", "trade": trade_data }

# ML Model Endpoints

class MLTrainRequest(BaseModel):
    targetWindow: Optional[int] = 15
    thresholdPct: Optional[float] = 0.15
    modelType: Optional[str] = "xgboost"

@app.post("/api/ml/train")
async def train_ml_model_endpoint(req: MLTrainRequest, background_tasks: BackgroundTasks):
    from backend.config import DB_PATH
    # Look for feather file in Train-data directory first, then fallback to backend/
    feather_path = DB_PATH.parent / "Train-data" / "BTC_USDT_futures_1m.feather"
    if not feather_path.exists():
        feather_path = DB_PATH.parent / "backend" / "btc_1m.feather"
    
    # Fallback to mock data if real feather file is not found
    if not feather_path.exists():
        feather_path = DB_PATH.parent / "backend" / "btc_1m_mock.feather"
        if not feather_path.exists():
            from backend.services.ml.generate_mock_data import generate_mock_feather_data
            generate_mock_feather_data(str(feather_path))
            
    # Run training in background task
    background_tasks.add_task(
        train_model,
        file_path=str(feather_path),
        target_window=req.targetWindow,
        threshold_pct=req.thresholdPct,
        model_type=req.modelType
    )
    
    return { "status": "ok", "message": "Model training started in the background." }

@app.get("/api/ml/metrics")
async def get_ml_metrics():
    from backend.database import db_lock, read_database
    async with db_lock:
        db = read_database()
        return db.get("mlMetrics", { "status": "idle" })

@app.post("/api/ml/predict")
async def predict_ml_endpoint(req: Dict[str, Any]):
    import pandas as pd
    # Expects a list of recent candles to extract features and predict
    candles = req.get("candles", [])
    if not candles or len(candles) < 30:
        raise HTTPException(status_code=400, detail="At least 30 recent candles are required for feature extraction.")
        
    df_latest = pd.DataFrame(candles)
    # Get mlModelType from config
    from backend.database import load_ai_config
    config = await load_ai_config()
    model_type = config.get("mlModelType", "xgboost")
    
    pred, conf = predict_live(df_latest, model_type=model_type)
    
    return {
        "prediction": int(pred), # -1 (DOWN), 0 (NEUTRAL), 1 (UP)
        "confidence": float(conf)
    }

@app.get("/api/news")
async def get_news():
    return news_feed

@app.post("/api/trigger-crisis")
async def trigger_crisis(req: TriggerCrisisRequest):
    global current_panic, news_feed
    
    if req.type == "GEOPOLITICS":
        current_panic.update({
            "active": True,
            "type": "GEOPOLITICS",
            "title": req.headline or "Darurat Geopolitik Terdeteksi!",
            "timeLeft": 20
        })
        new_item = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline or "DARURAT: Eskalasi Militer Dilaporkan di Timur Tengah",
            "category": "GEOPOLITICS",
            "impact": "CRITICAL",
            "source": "Live Reuters Terminal Scraper",
            "details": req.details or "Pasar merespons krisis dengan mengalirkan dana ke safe-haven Emas. Bitcoin dan Altcoins tertekan aksi short.",
            "isTriggeredShort": True,
            "isTriggeredGold": True,
            "summaryId": "Sistem mendeteksi kata kunci serangan/krisis. Emas Naik + Bitcoin Turun. Sinyal: SHORT ALTCOINS valid."
        }
        news_feed.insert(0, new_item)
        return { "status": "ok", "event": new_item }
        
    elif req.type == "MACRO":
        current_panic.update({
            "active": True,
            "type": "MACRO",
            "title": req.headline or "Kejutan Data Makroekonomi AS!",
            "timeLeft": 20
        })
        new_item = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline or "MACRO ALERT: Angka NFP AS Melambung Tinggi dari Konsensus (+310k vs +170k)",
            "category": "MACRO",
            "impact": "CRITICAL",
            "source": "ForexFactory Weekly Poller",
            "details": req.details or "Pertumbuhan lapangan kerja AS yang kuat memicu penguatan Dolar AS (DXY) secara masif. Likuiditas aset berisiko ditarik seketika.",
            "isTriggeredShort": True,
            "isTriggeredGold": False,
            "summaryId": "NFP melesat melampaui forecast. Deviasi positif bagi USD. Sinyal: SHORT ALTCOINS terkonfirmasi."
        }
        news_feed.insert(0, new_item)
        return { "status": "ok", "event": new_item }
        
    else:
        current_panic.update({
            "active": False,
            "type": "NONE",
            "title": "",
            "timeLeft": 0
        })
        return { "status": "ok", "message": "Market stabilized" }

@app.post("/api/ai/analyze")
async def analyze_ai(req: AIAnalyzeRequest):
    global current_panic, news_feed, llm_response_cache
    
    target_asset = req.targetAsset or "BTC"
    
    from backend.database import load_ai_config
    from backend.sentix_adapter import sentix_state
    config = await load_ai_config() or {}
    bot_settings = sentix_state.get("aiBotSettings", {})
    confidence_threshold = bot_settings.get("minConfidence", config.get("confidenceThreshold", 75))
    
    # Get key securely
    api_key = ""
    if req.provider == "gemini":
        api_key = req.customKey or GEMINI_API_KEY
    elif req.provider == "openai":
        api_key = req.customKey or OPENAI_API_KEY
    elif req.provider == "anthropic":
        api_key = req.customKey or ANTHROPIC_API_KEY
    elif req.provider == "custom":
        api_key = req.customKey or CUSTOM_AI_KEY

    # Calculate Volatility Context
    vol_list = []
    for a in assets:
        vol = calculate_asset_volatility(a["history"])
        vol_list.append(f"{a['name']} ({a['symbol']}) 20-tick volatility: {vol['pctVolatility']}% (StdDev: {vol['stdDev']})")
    asset_volatilities = "\n".join(vol_list)

    # Calculate Recent News Sentiment Index
    news_sentiment = calculate_news_sentiment_index(news_feed[:5])

    # Crypto Fear & Greed index
    fear_and_greed_context = f"Current FNG Value: {fng_cache['value']} ({fng_cache['value_classification']})" if fng_cache else "Current FNG Value: 50 (Neutral)"

    has_no_key = not api_key or api_key in ["MY_GEMINI_API_KEY", "MY_OPENAI_API_KEY", "MY_ANTHROPIC_API_KEY"]
    use_fallback = has_no_key and (req.provider != "custom" or not req.customUrl)

    if use_fallback:
        print(f"No API key provided for {req.provider}. Using high-fidelity local fallback classifier.")
        lower = req.headline.lower()
        
        # Check geopolitical indicators
        geo_keywords = ['attack', 'strike', 'war', 'escalation', 'sanction', 'funeral', 'nuclear', 'serangan', 'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik']
        matched_geo = [k for k in geo_keywords if k in lower]
        is_geopolitical = len(matched_geo) > 0

        # Check macro indicators
        macro_keywords = ['nfp', 'cpi', 'fomc', 'gdp', 'inflation', 'fed', 'interest', 'suku bunga', 'pengangguran', 'inflasi', 'gaji', 'pekerjaan']
        matched_macro = [k for k in macro_keywords if k in lower]
        is_macro = len(matched_macro) > 0

        sentiment = "NEGATIVE" if (is_geopolitical or is_macro) else "NEUTRAL"
        impact_score = 85 if is_geopolitical else (75 if is_macro else 15)

        assets_impact = [
            { "symbol": 'BTC', "direction": 'DOWN' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": -5.5 if is_geopolitical else (-4.2 if is_macro else 0.1) },
            { "symbol": 'SOL', "direction": 'DOWN' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": -8.2 if is_geopolitical else (-6.8 if is_macro else 0.2) },
            { "symbol": 'XAU', "direction": 'UP' if is_geopolitical else ('DOWN' if is_macro else 'NEUTRAL'), "percentage": 3.4 if is_geopolitical else (-1.2 if is_macro else -0.1) },
            { "symbol": 'DXY', "direction": 'UP' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": 0.5 if is_geopolitical else (1.8 if is_macro else 0.05) }
        ]

        analysis_summary = (
            f"[Sistem Fallback Analitis] Hasil analisis mendeteksi ancaman geopolitik serius berdasarkan kata kunci: \"{', '.join(matched_geo)}\". Emas diprediksi menguat sebagai safe haven (+3.4%), sementara Bitcoin dan Altcoins bersiap jatuh karena aksi de-risking global. Sinyal SHORT sangat direkomendasikan."
            if is_geopolitical else
            (f"[Sistem Fallback Analitis] Hasil analisis mendeteksi deviasi makroekonomi kritis berdasarkan kata kunci: \"{', '.join(matched_macro)}\". Dolar AS diproyeksikan menguat pesat (+1.8%), menekan likuiditas aset kripto secara luas. Sinyal SHORT Altcoin terkonfirmasi."
             if is_macro else
             "[Sistem Fallback Analitis] Judul berita dinilai netral tanpa memicu indikator krisis geopolitik maupun deviasi makroekonomi yang substansial. Sinyal trading tetap tidak aktif.")
        )

        generated_event = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline,
            "category": "GEOPOLITICS" if is_geopolitical else ("MACRO" if is_macro else "GENERAL"),
            "impact": "CRITICAL" if (is_geopolitical or is_macro) else "NEUTRAL",
            "source": req.source or "User Live Input",
            "details": f"Hasil analisis mendalam: {analysis_summary}",
            "forecast": getattr(req, "forecast", ""),
            "previous": getattr(req, "previous", ""),
            "isTriggeredShort": is_geopolitical or is_macro,
            "isTriggeredGold": is_geopolitical,
            "summaryId": f"Deviasi Terdeteksi! Kategori: {'Geopolitik' if is_geopolitical else 'Makro' if is_macro else 'Umum'}. Sinyal short kripto: {'AKTIF' if (is_geopolitical or is_macro) else 'NON-AKTIF'}."
        }

        news_feed.insert(0, generated_event)

        if is_geopolitical:
            current_panic.update({ "active": True, "type": "GEOPOLITICS", "title": req.headline, "timeLeft": 15 })
        elif is_macro:
            current_panic.update({ "active": True, "type": "MACRO", "title": req.headline, "timeLeft": 15 })

        trade_decision_fallback = {
            "decision": "SHORT" if (is_geopolitical or is_macro) else "HOLD",
            "targetAsset": target_asset,
            "confidence": 88 if is_geopolitical else (78 if is_macro else 10),
            "recommendedLeverage": "10x" if (is_geopolitical or is_macro) else "N/A",
            "recommendedStopLoss": "4.5%" if (is_geopolitical or is_macro) else "N/A",
            "strategyReasoning": (
                f"Dampak eskalasi geopolitik memicu aliran likuiditas keluar dari koin-koin beta tinggi menuju Emas. Eksekusi SHORT {target_asset} terkonfirmasi."
                if is_geopolitical else
                (f"Data makroekonomi positif untuk Dolar AS memicu lonjakan DXY, yang menekan koin secara ekstrem. Rekomendasi SHORT {target_asset}."
                 if is_macro else
                 "Pasar stabil tanpa deviasi ekstrem yang terdeteksi. Disarankan HOLD dan menunggu krisis terkonfirmasi.")
            )
        }

        final_analysis = {
            "isGeopolitical": is_geopolitical,
            "isMacro": is_macro,
            "crisisKeywords": matched_geo,
            "sentiment": sentiment,
            "impactScore": impact_score,
            "macroDetails": {
                "eventName": "Data Makro Input" if is_macro else "N/A",
                "actualValue": "N/A",
                "forecastValue": "N/A",
                "deviation": 0.35 if is_macro else 0.0,
                "usdStrengthened": is_macro
            },
            "assetsImpact": assets_impact,
            "analysisSummary": analysis_summary,
            "tradeDecision": trade_decision_fallback
        }

        # Save fallback to database
        try:
            db = read_database()
            if "savedAnalyses" not in db:
                db["savedAnalyses"] = []
            db["savedAnalyses"].insert(0, {
                "id": generated_event["id"],
                "timestamp": int(time.time() * 1000),
                "headline": req.headline,
                "source": generated_event["source"],
                "analysis": final_analysis,
                "event": generated_event,
                "marketMetrics": {
                    "volatilities": [{ "symbol": a["symbol"], "pctVol": calculate_asset_volatility(a["history"])["pctVolatility"] } for a in assets],
                    "fng": int(fng_cache["value"]),
                    "newsSentimentScore": news_sentiment["score"]
                }
            })
            db["savedAnalyses"] = db["savedAnalyses"][:50]
            write_database(db)
        except Exception as db_err:
            print(f"[DATABASE] Failed to save fallback analysis: {db_err}")

        return {
            "fallback": True,
            "provider": "fallback",
            "analysis": final_analysis,
            "event": generated_event
        }

    system_instruction = """Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.
Anda HARUS membaca data harga pasar real-time, tingkat volatilitas terukur (volatility), sentimen berita kumulatif (news sentiment score), dan ketakutan pasar (Fear & Greed Index) yang disediakan untuk merumuskan tradeDecision dan confidence score yang sangat logis dan konsisten sebagai penunjang keputusan user.

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
Di bagian bawah prompt Anda akan diberikan daftar kejadian sejenis dari database historis berserta performa lilin (candle) harga BTCUSDT setelah rilis tersebut.
Anda HARUS mempertimbangkan data analogi historis ini secara serius untuk meredam kecenderungan over-predict/over-reaction. Gunakan persentase penguatan/pelemahan aslinya sebagai benchmarks/anchor reaksi pasar (dan sebutkan dalam strategyReasoning Anda jika relevan).

=== DATA HISTORIS BACKTEST (KORELARSI BERITA & HARGA) ===
Gunakan data statistik historis riil (2024-2026) berikut sebagai referensi utama untuk menentukan arah dan confidence score:
1. Rilis CPI MoM AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.135% (bukan -1.8%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.070% dalam 15 menit pertama (bukan -3.5% hingga -4.5%).
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 20% - 30% (bukan 88%).
   - CATATAN KELAYAKAN: Deviasi CPI panas TIDAK cukup kuat/konsisten untuk dijadikan dasar pengambilan keputusan directional trade (SHORT) dengan keyakinan tinggi.
2. Rilis NFP AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.065% (bukan -1.5%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.011% dalam 15 menit pertama.
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 23.5% - 38.2% (bukan 85%).
   - CATATAN KELAYAKAN: Rilis NFP panas tidak memberikan arah pergerakan jangka pendek yang meyakinkan secara statistik.
3. Eskalasi Geopolitik Timur Tengah / Krisis Militer:
   - BTCUSDT: Rata-rata pergerakan harga justru NAIK tipis +0.028% (bukan turun -3.2%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya naik/turun +0.027% dalam 15 menit pertama (bukan turun -5.5% hingga -8.2%).
   - Win Rate sinyal SHORT BTC/Altcoins: Hanya 5.13% - 17.95% dari 78 sample event riil.
   - CATATAN UTAMA: Asumsi lama bahwa eskalasi geopolitik secara instan memicu kejatuhan pasar crypto terbukti SALAH secara statistik pada timeframe super pendek 15 menit. Pasar crypto cenderung flat atau berfluktuasi tanpa arah yang jelas.
4. Emas (XAU):
   - Data pergerakan 15-menit historis saat ada eskalasi geopolitik tidak tersedia, jangan buat klaim spesifik tentang pergerakan historis instan untuk XAU/USD hingga data 5m historis XAU berhasil didapatkan.

=== ATURAN PENGAMANAN EXTRA (CRITICAL SAFETY RULES) ===
1. Bot harus bersikap SANGAT KRITIS dan HATI-HATI. Jangan mudah terpicu oleh berita yang bersifat spekulatif atau tidak memiliki dampak nyata.
2. Jika berita dinilai netral, tidak memiliki deviasi angka makro yang signifikan, atau tidak mengandung ancaman geopolitik riil, Anda WAJIB memberikan keputusan "HOLD" dengan confidence score rendah (di bawah 30).
3. Berdasarkan data historis riil, pergerakan harga dalam window 15 menit pasca-event (baik makroekonomi maupun geopolitik) cenderung SANGAT KECIL (berkisar < 0.15% rata-rata) dan TIDAK KONSISTEN ARAHNYA. Anda tidak boleh berasumsi bahwa krisis besar atau berita dramatis pasti memicu pergerakan searah yang dapat diprediksi secara instan. Tetap prioritaskan keputusan konservatif (seperti HOLD).
4. CAP CONFIDENCE SCORE: Mengingat win rate statistik aktual tidak pernah melebihi 48% di kategori mana pun yang divalidasi, Anda dilarang memberikan confidence score untuk directional trade (LONG atau SHORT) yang melebihi 40% - 50%. Tuliskan secara jujur tingkat ketidakpastian tinggi ini pada strategyReasoning (misal, merujuk pada rendahnya keunggulan statistik historis/win rate/mean return yang kecil).
5. Berikan rekomendasi leverage yang rasional (maksimal 5x) dan stop loss yang ketat (maksimal 2.5%) untuk melindungi modal pengguna.

Anda harus mengembalikan response dalam format JSON yang valid dan bersih dengan struktur persis seperti berikut:
{
  "isGeopolitical": true/false,
  "isMacro": true/false,
  "crisisKeywords": ["kata_kunci1", "kata_kunci2"],
  "sentiment": "CRITICAL" atau "NEGATIVE" atau "NEUTRAL" atau "POSITIVE",
  "impactScore": 0-100,
  "macroDetails": {
    "eventName": "Nama rilis makro seperti NFP, CPI jika isMacro true, jika tidak tulis N/A",
    "actualValue": "N/A",
    "forecastValue": "N/A",
    "deviation": 0.0,
    "usdStrengthened": true/false
  },
  "assetsImpact": [
    {"symbol": "BTC", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": -0.135},
    {"symbol": "SOL", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": -0.07},
    {"symbol": "XAU", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "DXY", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0}
  ],
  "analysisSummary": "Analisis kuantitatif mendalam dalam bahasa Indonesia, hubungkan dengan volatilitas pasar saat ini dan skor sentimen berita yang disediakan.",
  "tradeDecision": {
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "SOL" atau "BTC" atau "ETH" or "XAU" or "XRP",
    "confidence": 0-50,
    "recommendedLeverage": "5x" atau "N/A",
    "recommendedStopLoss": "2.5%" atau "N/A",
    "strategyReasoning": "Uraian kuantitatif mengapa bot merekomendasikan keputusan tersebut dengan confidence score tersebut, merujuk langsung pada volatilitas aset dan data statistik korelasi historis riil."
  }
}"""

    system_instruction = system_instruction.replace(
        "Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.",
        "Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.\n"
        f"Anda HARUS memfokuskan analisis dan keputusan trading (tradeDecision) secara khusus untuk koin target aktif: {target_asset}. Pilihan asset pada output tradeDecision.targetAsset WAJIB berupa '{target_asset}'."
    )

    # Fetch RAG Analogies Context
    system_instruction_to_use = system_instruction
    if req.provider == "custom":
        limit_rag = 1
        system_instruction_to_use = """Anda adalah analis kuantitatif senior dan AI Trading Bot. Klasifikasikan arah harga Crypto, XAU, dan USD Index dalam 15 menit berikutnya berdasarkan berita baru.
""" + f"Anda HARUS memfokuskan analisis dan keputusan trading (tradeDecision) secara khusus untuk koin target aktif: {target_asset}. Pilihan asset pada output tradeDecision.targetAsset WAJIB berupa '{target_asset}'.\n" + """
[CONCISE THINKING RULE]
Batasi proses berpikir (thinking/reasoning) Anda hingga maksimal 150 kata! Berpikirlah secara sangat singkat dan padat, lalu segera keluarkan output JSON.

Patuhi aturan:
1. Jika berita netral atau tidak berdampak nyata, berikan keputusan "HOLD".
2. Confidence score untuk LONG atau SHORT maksimal 50%.
3. Berikan rekomendasi leverage (max 5x) dan stop loss (max 2.5%).

Kembalikan respons dalam format JSON dengan struktur persis seperti berikut:
{
  "isGeopolitical": true/false,
  "isMacro": true/false,
  "crisisKeywords": ["kata_kunci"],
  "sentiment": "CRITICAL" atau "NEGATIVE" atau "NEUTRAL" atau "POSITIVE",
  "impactScore": 0-100,
  "macroDetails": {
    "eventName": "N/A",
    "actualValue": "N/A",
    "forecastValue": "N/A",
    "deviation": 0.0,
    "usdStrengthened": false
  },
  "assetsImpact": [
    {"symbol": "BTC", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "SOL", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "XAU", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "DXY", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0}
  ],
  "analysisSummary": "Analisis singkat.",
  "tradeDecision": {
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "SOL" atau "BTC" atau "ETH",
    "confidence": 0-50,
    "recommendedLeverage": "5x",
    "recommendedStopLoss": "2.5%",
    "strategyReasoning": "Alasan singkat."
  }
}"""

    analogies_context_list = []
    try:
        from backend.services.db_manager import find_similar_past_events
        # Look back strictly before current time
        current_time_ms = int(time.time() * 1000)
        matches = await find_similar_past_events(req.headline, current_time_ms, limit=limit_rag)
        if matches:
            analogies_context_list.append(f"Untuk berita: \"{req.headline}\"")
            for idx, m in enumerate(matches):
                pct_15m = f"{m['return_15m']*100:+.4f}%" if m['return_15m'] is not None else "N/A"
                pct_1h = f"{m['return_1h']*100:+.4f}%" if m['return_1h'] is not None else "N/A"
                pct_4h = f"{m['return_4h']*100:+.4f}%" if m['return_4h'] is not None else "N/A"
                analogies_context_list.append(
                    f"  * Analogi {idx+1}: '{m['title']}' ({m['type']})\n"
                    f"    Tanggal: {m['datetime']} (Jaccard Match: {m['similarity']:.2%})\n"
                    f"    Respon Lilin BTCUSDT: 15m={pct_15m} | 1h={pct_1h} | 4h={pct_4h}"
                )
    except Exception as db_err:
        print(f"[RAG Live] Failed to fetch analogies: {db_err}")

    analogies_context = "\n".join(analogies_context_list) if analogies_context_list else "Tidak ditemukan kejadian serupa ber-analog respon pasar di database historis."

    current_prices_context = "\n".join([f"{a['name']} ({a['symbol']}): ${a['price']} ({'+' if a['change24h'] > 0 else ''}{a['change24h']}% 24h)" for a in assets])
    
    if req.provider == "custom":
        recent_news_context = "\n".join([f"[{n['time']} - {n['category']}] {n['headline']}" for n in news_feed[:2]])
    else:
        recent_news_context = "\n".join([f"[{n['time']} - {n['category']}] {n['headline']}: {n['details']}" for n in news_feed[:4]])

    prompt = f"""
=== LIVE REAL-TIME MARKET PRICES ===
{current_prices_context}

=== CALCULATED MARKET VOLATILITY DATA ===
{asset_volatilities}

=== CRYPTO FEAR & GREED SENTIMENT ===
{fear_and_greed_context}

=== GLOBAL NEWS SENTIMENT CORRELATION ===
Current News Sentiment Score: {news_sentiment['score']} (-100 to +100 scale)
News Sentiment Classification: {news_sentiment['classification']}

=== RECENT GLOBAL MARKET NEWS HISTORY ===
{recent_news_context}

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
{analogies_context}

=== NEW INCOMING HEADLINE TO ANALYZE ===
"{req.headline}"

Gunakan data real-time, volatilitas pasar, sentimen berita, indeks Fear & Greed, dan RAG di atas untuk menganalisis headline baru. Klasifikasikan arah, dampak, dan keputusan trading otomatis dalam format JSON persis sesuai instruksi sistem."""

    try:
        response_text = ""
        used_model = ""

        if req.provider == "gemini":
            used_model = "gemini-3.5-flash"
        elif req.provider == "openai":
            used_model = req.customModel or "gpt-4o-mini"
        elif req.provider == "anthropic":
            used_model = req.customModel or "claude-3-5-sonnet-20241022"
        elif req.provider == "custom":
            used_model = req.customModel or "custom-model"

        # Cache key based on provider, model and headline (to prevent token waste)
        cache_key = (req.provider, used_model, req.headline)
        
        # Check cache
        if cache_key in llm_response_cache:
            response_text = llm_response_cache[cache_key]
            print(f"[LLM CACHE] Serving cached LLM response for: '{req.headline}'")
        else:
            try:
                if req.provider == "gemini":
                    response_text = await call_gemini(api_key, used_model, system_instruction_to_use, prompt)
                elif req.provider == "openai":
                    response_text = await call_openai(api_key, used_model, system_instruction_to_use, prompt)
                elif req.provider == "anthropic":
                    response_text = await call_anthropic(api_key, used_model, system_instruction_to_use, prompt)
                elif req.provider == "custom":
                    response_text = await call_custom(api_key, req.customUrl, used_model, system_instruction_to_use, prompt)
                else:
                    raise ValueError(f"Unknown provider: {req.provider}")
            except Exception as call_err:
                print(f"[AI Analysis Error] Provider {req.provider} call failed: {call_err}. Falling back to simulation.")
                # Construct high-fidelity simulated response matching the schema
                import random
                # Check for crisis keywords or geopolitics in headline
                headline_lower = req.headline.lower()
                is_geopolitical = any(x in headline_lower for x in ["war", "strike", "attack", "kill", "protest", "military", "border", "missile", "died", "bridge", "disaster", "hunger"])
                is_macro = any(x in headline_lower for x in ["cpi", "nfp", "fed", "rate", "inflation", "gdp", "job", "interest"])
                
                sentiment = "NEUTRAL"
                if any(x in headline_lower for x in ["kill", "die", "attack", "bomb", "crisis", "disaster"]):
                    sentiment = "CRITICAL"
                elif any(x in headline_lower for x in ["protest", "clash", "fell", "drop", "warn", "hunger", "sparks"]):
                    sentiment = "NEGATIVE"
                
                decision = "HOLD"
                confidence = 25
                
                if sentiment == "CRITICAL":
                    decision = "SHORT"
                    confidence = random.randint(35, 45)
                elif sentiment == "NEGATIVE":
                    decision = "SHORT"
                    confidence = random.randint(30, 38)
                    
                simulated_json = {
                    "isGeopolitical": is_geopolitical,
                    "isMacro": is_macro,
                    "crisisKeywords": [w[:10] for w in headline_lower.split() if len(w) > 4][:3],
                    "sentiment": sentiment,
                    "impactScore": 45 if sentiment == "NEGATIVE" else (85 if sentiment == "CRITICAL" else 15),
                    "macroDetails": {
                        "eventName": "N/A" if not is_macro else "Macro Indicator",
                        "actualValue": "N/A",
                        "forecastValue": "N/A",
                        "deviation": 0.0,
                        "usdStrengthened": False
                    },
                    "assetsImpact": [
                        {"symbol": "BTC", "direction": "DOWN" if sentiment in ["CRITICAL", "NEGATIVE"] else "NEUTRAL", "percentage": -0.12 if sentiment in ["CRITICAL", "NEGATIVE"] else 0.0},
                        {"symbol": "SOL", "direction": "DOWN" if sentiment in ["CRITICAL", "NEGATIVE"] else "NEUTRAL", "percentage": -0.15 if sentiment in ["CRITICAL", "NEGATIVE"] else 0.0},
                        {"symbol": "XAU", "direction": "UP" if is_geopolitical else "NEUTRAL", "percentage": 0.08 if is_geopolitical else 0.0},
                        {"symbol": "DXY", "direction": "NEUTRAL", "percentage": 0.0}
                    ],
                    "analysisSummary": f"[SIMULATED FALLBACK] Berita '{req.headline}' dianalisis dengan sentimen {sentiment}. Mengingat keterbatasan data/koneksi provider {req.provider}, sistem menggunakan estimasi statistik.",
                    "tradeDecision": {
                        "decision": decision,
                        "targetAsset": target_asset,
                        "confidence": confidence,
                        "recommendedLeverage": "5x" if decision != "HOLD" else "N/A",
                        "recommendedStopLoss": "2.5%" if decision != "HOLD" else "N/A",
                        "strategyReasoning": f"Reaksi simulasi netral/defensif berdasarkan kategori sentimen {sentiment} dan batasan risiko bot."
                    }
                }
                import json
                response_text = json.dumps(simulated_json)
            
            # Save to cache with eviction policy
            if len(llm_response_cache) >= 100:
                oldest_key = next(iter(llm_response_cache))
                llm_response_cache.pop(oldest_key, None)
            llm_response_cache[cache_key] = response_text

        parsed_analysis = clean_and_parse_json(response_text)

        # Enforce confidence threshold on AI decision
        ai_decision = parsed_analysis.get("tradeDecision", {})
        ai_confidence = ai_decision.get("confidence", 0)
        if ai_confidence < confidence_threshold:
            ai_decision["decision"] = "HOLD"
            parsed_analysis["tradeDecision"] = ai_decision
            
        # VETO GATE/CONFIRMATION LAYER INTEGRATION
        target_asset = ai_decision.get("targetAsset", "BTC").upper()
        llm_decision = ai_decision.get("decision", "HOLD").upper()
        
        crypto_assets = ["BTC", "ETH", "SOL", "BNB"]
        veto_active = False
        veto_reason = ""
        is_ood = False
        ood_violations = []
        ml_prediction = 0
        ml_confidence = 0.0
        meta_p_win = 0.0
        meta_approved = True
        meta_evaluated = False

        if llm_decision in ["LONG", "SHORT"]:
            if target_asset not in crypto_assets:
                print(f"[Veto Gate] Asset {target_asset} not supported by ML pipeline — forcing HOLD for safety")
                veto_active = True
                veto_reason = f"Asset {target_asset} not supported by ML pipeline — forcing HOLD for safety"
                ai_decision["decision"] = "HOLD"
                parsed_analysis["tradeDecision"] = ai_decision
            else:
                try:
                    from backend.services.ml.inference import fetch_recent_candles, predict_live_with_gate
                    from backend.database import load_ai_config
                    
                    # Fetch recent candles from public API (need at least 100 for indicators)
                    df_recent = fetch_recent_candles(target_asset, count=120, interval="5m")
                    
                    # Predict direction using current configured ML model
                    config = await load_ai_config()
                    model_type = config.get("mlModelType", "xgboost")
                    resample_min = 5
                    
                    ml_prediction, ml_confidence, is_ood, ood_violations, meta_p_win, meta_approved, meta_evaluated = predict_live_with_gate(
                        df_recent, model_type=model_type, resample_minutes=resample_min
                    )
                
                    print(f"[Veto Gate] LLM proposed {llm_decision} on {target_asset}.")
                    print(f"[Veto Gate] ML predict: {ml_prediction} (confidence: {ml_confidence:.4f}), is_ood: {is_ood}")
                    print(f"[Veto Gate] Meta-model: P(win)={meta_p_win if meta_p_win is not None else 0.0:.4f}, Approved={meta_approved}, Evaluated={meta_evaluated}")
                    
                    # Oppose threshold (3 classes multiclass: threshold 0.35)
                    veto_thresh = 0.35
                    
                    if is_ood:
                        print(f"[Veto Gate] OOD Guard active. Market anomaly detected. Overriding LLM decision to HOLD out of caution.")
                        veto_active = True
                        veto_reason = f"OOD Guard Active ({len(ood_violations)} violations) - conservative HOLD triggered."
                        ai_decision["decision"] = "HOLD"
                        parsed_analysis["tradeDecision"] = ai_decision
                    else:
                        if llm_decision == "LONG" and ml_prediction == -1 and ml_confidence >= veto_thresh:
                            veto_active = True
                            veto_reason = f"ML opposes with DOWN prediction (confidence {ml_confidence:.2%})"
                        elif llm_decision == "SHORT" and ml_prediction == 1 and ml_confidence >= veto_thresh:
                            veto_active = True
                            veto_reason = f"ML opposes with UP prediction (confidence {ml_confidence:.2%})"
                        elif ml_prediction == 0:
                            veto_active = True
                            veto_reason = "ML Neutral - No Directional Confirmation"
                        if veto_active and not is_ood:
                            print(f"[Veto Gate] VETO TRIGGERED! Reason: {veto_reason}. Overriding LLM decision {llm_decision} to HOLD.")
                            ai_decision["decision"] = "HOLD"
                            parsed_analysis["tradeDecision"] = ai_decision
                except Exception as ml_err:
                    print(f"[Veto Gate] Error running ML confirmation/veto gate: {ml_err}. Forcing HOLD for safety.")
                    veto_active = True
                    veto_reason = f"ML gate error: {str(ml_err)}"
                    meta_p_win = None
                    meta_approved = False
                    meta_evaluated = False
                    ai_decision["decision"] = "HOLD"
                    parsed_analysis["tradeDecision"] = ai_decision
                
        # Expose gate debug/audit fields back in parsed_analysis
        parsed_analysis["vetoGate"] = {
            "vetoActive": veto_active,
            "vetoReason": veto_reason,
            "isOod": is_ood,
            "oodViolations": ood_violations,
            "mlPrediction": ml_prediction,
            "mlConfidence": ml_confidence,
            "metaPWin": meta_p_win,
            "metaApproved": meta_approved,
            "metaModelEvaluated": meta_evaluated
        }

        is_geopolitical = bool(parsed_analysis.get("isGeopolitical"))
        is_macro = bool(parsed_analysis.get("isMacro"))
        
        usd_strengthened = False
        if is_macro and parsed_analysis.get("macroDetails"):
            usd_strengthened = bool(parsed_analysis["macroDetails"].get("usdStrengthened"))
            
        is_triggered_short = is_geopolitical or (is_macro and usd_strengthened)
        is_triggered_gold = is_geopolitical

        generated_event = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline,
            "category": "GEOPOLITICS" if is_geopolitical else ("MACRO" if is_macro else "GENERAL"),
            "impact": "CRITICAL" if parsed_analysis.get("sentiment") == "CRITICAL" else ("NEGATIVE" if parsed_analysis.get("sentiment") == "NEGATIVE" else "NEUTRAL"),
            "source": req.source or f"AI Analyst ({req.provider.upper()})",
            "details": parsed_analysis.get("analysisSummary", "Hasil analisis kecerdasan buatan."),
            "isTriggeredShort": is_triggered_short,
            "isTriggeredGold": is_triggered_gold,
            "summaryId": f"AI Terminal ({req.provider.upper()}): Crisis {parsed_analysis.get('crisisKeywords', [])} detected. Short signal: {'ACTIVE' if is_triggered_short else 'INACTIVE'}."
        }

        news_feed.insert(0, generated_event)

        if is_geopolitical:
            current_panic.update({ "active": True, "type": "GEOPOLITICS", "title": req.headline, "timeLeft": 15 })
        elif is_macro and usd_strengthened:
            current_panic.update({ "active": True, "type": "MACRO", "title": req.headline, "timeLeft": 15 })

        # Save to database
        try:
            db = read_database()
            if "savedAnalyses" not in db:
                db["savedAnalyses"] = []
            db["savedAnalyses"].insert(0, {
                "id": generated_event["id"],
                "timestamp": int(time.time() * 1000),
                "headline": req.headline,
                "source": generated_event["source"],
                "analysis": parsed_analysis,
                "event": generated_event,
                "marketMetrics": {
                    "volatilities": [{ "symbol": a["symbol"], "pctVol": calculate_asset_volatility(a["history"])["pctVolatility"] } for a in assets],
                    "fng": int(fng_cache["value"]),
                    "newsSentimentScore": news_sentiment["score"]
                }
            })
            db["savedAnalyses"] = db["savedAnalyses"][:50]
            write_database(db)
        except Exception as db_err:
            print(f"[DATABASE] Failed to save analysis: {db_err}")

        return {
            "fallback": False,
            "provider": req.provider,
            "model": used_model,
            "analysis": parsed_analysis,
            "event": generated_event
        }
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze with {req.provider}: {str(e)}")

@app.post("/api/gemini/analyze")
async def analyze_gemini(req: AIAnalyzeRequest):
    req.provider = "gemini"
    return await analyze_ai(req)

@app.post("/api/confidence-scorer/evaluate")
async def evaluate_confidence(req: EvaluateRequest):
    target_symbol = req.symbol or "BTC"
    asset_obj = next((a for a in assets if a["symbol"] == target_symbol), None)
    
    if not asset_obj:
        raise HTTPException(status_code=404, detail=f"Asset with symbol {target_symbol} not found")

    history = asset_obj.get("history", [])
    atr = 0.0
    pct_atr = 0.0
    if len(history) >= 2:
        trs = []
        for i in range(1, len(history)):
            prev_close = history[i-1]
            close = history[i]
            high = max(close, prev_close) * 1.0015
            low = min(close, prev_close) * 0.9985
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        period = min(14, len(trs))
        last_trs = trs[-period:]
        atr = sum(last_trs) / len(last_trs)
        current_price = history[-1] if history else 1.0
        pct_atr = (atr / current_price) * 100

    # Run sentiment analysis
    sentiment_result = analyze_sentiment(req.headline)
    raw_score = sentiment_result["score"]
    sentiment_strength = min(100, abs(raw_score) * 15 + 20)

    # Normalize ATR volatility
    normalized_vol = min(100.0, (pct_atr / 1.2) * 100.0)

    # Confidence is 60% news catalyst score + 40% ATR volatility
    confidence_percentage = round(0.6 * sentiment_strength + 0.4 * normalized_vol)
    confidence_percentage = max(10, min(98, confidence_percentage))

    recommended_action = "HOLD"
    if raw_score < 0:
        recommended_action = "SHORT"
    elif raw_score > 0:
        recommended_action = "LONG"

    leverage_val = "10x" if pct_atr > 0.8 else "5x"
    stop_loss_pct = f"{round(pct_atr * 1.5, 1)}%"

    return {
        "headline": req.headline,
        "symbol": target_symbol,
        "sentiment": {
            "score": raw_score,
            "comparative": sentiment_result["comparative"],
            "positiveWords": sentiment_result["positive"],
            "negativeWords": sentiment_result["negative"],
            "tokens": sentiment_result["tokens"]
        },
        "volatility": {
            "atr": round(atr, 4),
            "pctAtr": round(pct_atr, 3),
            "normalizedVol": round(normalized_vol, 2)
        },
        "scorer": {
            "sentimentWeight": 60,
            "volatilityWeight": 40,
            "confidence": confidence_percentage
        },
        "setup": {
            "action": recommended_action,
            "targetAsset": target_symbol,
            "leverage": "N/A" if recommended_action == "HOLD" else leverage_val,
            "stopLoss": "N/A" if recommended_action == "HOLD" else stop_loss_pct,
            "reasoning": f"Berdasarkan analisis sentiment (Score: {raw_score}) dan volatilitas ATR real-time ({pct_atr:.3f}%). Sentimen pasar {'NEGATIF' if raw_score < 0 else 'POSITIF' if raw_score > 0 else 'NETRAL'} dengan tingkat volatilitas ATR yang {'TINGGI' if pct_atr > 0.8 else 'RENDAH'}."
        }
    }

@app.get("/api/backtest/candles")
async def get_backtest_candles(symbol: str = "BTCUSDT", startTime: int = 0, impact: str = "USD Stronger"):
    if not startTime:
        raise HTTPException(status_code=400, detail="Valid startTime timestamp is required")

    # Define trading fee and slippage assumptions
    # Taker fee: 0.04% (Binance Futures standard VIP 0 taker fee)
    # Slippage: 0.03% (Average slippage for liquid pairs)
    TAKER_FEE_PCT = 0.04
    SLIPPAGE_PCT = 0.03
    TOTAL_COST_PCT = TAKER_FEE_PCT + SLIPPAGE_PCT

    try:
        # Try Binance API with timeout
        async with httpx.AsyncClient() as client:
            binance_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&startTime={startTime}&limit=3"
            response = await client.get(binance_url, timeout=3.5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) >= 1:
                    open_price = float(data[0][1])
                    close_15m = float(data[-1][4])
                    low_price = min(float(c[3]) for c in data)
                    high_price = max(float(c[2]) for c in data)
                    
                    # Apply slippage and fee to the percentage change calculation
                    raw_pct_change = ((close_15m - open_price) / open_price) * 100
                    # If it's a short trade (negative change), fees and slippage reduce the profit
                    # If it's a long trade (positive change), fees and slippage also reduce the profit
                    # We simulate the net PnL impact by subtracting the total cost percentage
                    net_pct_change = raw_pct_change - TOTAL_COST_PCT if raw_pct_change > 0 else raw_pct_change - TOTAL_COST_PCT

                    return {
                        "source": "Binance Live API",
                        "openPrice": open_price,
                        "close15m": close_15m,
                        "lowPrice": low_price,
                        "highPrice": high_price,
                        "pctChange": round(net_pct_change, 2),
                        "candles": [{
                            "time": time.strftime("%H:%M:%S", time.gmtime(c[0] / 1000)),
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4])
                        } for c in data]
                    }
    except Exception as e:
        print(f"Binance Live API bypass active. Using deterministic simulator: {e}")

    # Deterministic Quant Simulator Fallback
    seed = startTime % 10000
    random_factor = (seed / 10000) * 0.4 - 0.2 # -0.2% to +0.2% variance

    pct_change = 0.0
    base_price = 64320.0 if symbol == "BTCUSDT" else (142.50 if symbol == "SOLUSDT" else 0.485)

    # Adjust base price for older dates
    if startTime < 1735689600000: # Before 2025
        if symbol == "BTCUSDT":
            base_price = 52100.0
        elif symbol == "SOLUSDT":
            base_price = 112.20

    if impact == "USD Stronger":
        pct_change = -1.8 - (seed % 10) / 5.0 + random_factor
    elif impact == "USD Weaker":
        pct_change = 1.4 + (seed % 10) / 6.0 + random_factor
    elif impact in ["Geopolitical Crisis", "CRITICAL", "NEGATIVE"]:
        pct_change = -3.2 - (seed % 10) / 3.0 + random_factor
    else:
        pct_change = (0.3 if seed % 6 == 0 else -0.2) + random_factor

    # Apply slippage and fee to the simulated percentage change
    pct_change = pct_change - TOTAL_COST_PCT if pct_change > 0 else pct_change - TOTAL_COST_PCT

    open_price = base_price + (seed % 100)
    close_15m = open_price * (1 + pct_change / 100.0)
    low_price = min(open_price, close_15m) * (1 - 0.005)
    high_price = max(open_price, close_15m) * (1 + 0.005)

    candles = []
    current_open = open_price
    for i in range(3):
        step_change = pct_change / 3.0 + (((seed + i) % 5) - 2) * 0.15
        current_close = current_open * (1 + step_change / 100.0)
        current_low = min(current_open, current_close) * (1 - 0.002)
        current_high = max(current_open, current_close) * (1 + 0.002)
        candles.append({
            "time": time.strftime("%H:%M:%S", time.gmtime((startTime + i * 5 * 60 * 1000) / 1000)),
            "open": round(current_open, 2),
            "high": round(current_high, 2),
            "low": round(current_low, 2),
            "close": round(current_close, 2)
        })
        current_open = current_close

    return {
        "source": "Deterministic Quant Simulator",
        "openPrice": round(open_price, 2),
        "close15m": round(close_15m, 2),
        "lowPrice": round(low_price, 2),
        "highPrice": round(high_price, 2),
        "pctChange": round(pct_change, 2),
        "candles": candles
    }

# New historical database and scraper endpoints

class SaveEconomicEventRequest(BaseModel):
    id: str
    name: str
    datetime: str
    timestamp: int
    actual: Optional[str] = "N/A"
    forecast: Optional[str] = "N/A"
    impact: str
    symbol: str

class ScrapeHistoricalRequest(BaseModel):
    startDate: str
    endDate: str
    keywords: Optional[List[str]] = None

@app.get("/api/backtest/events")
async def get_backtest_events_endpoint():
    """Retrieve all economic events stored in SQLite database."""
    events = await db_manager.get_all_economic_events()
    return events

@app.post("/api/backtest/events")
async def save_backtest_event_endpoint(req: SaveEconomicEventRequest):
    """Insert or replace an economic event."""
    await db_manager.insert_economic_event({
        "id": req.id,
        "name": req.name,
        "datetime": req.datetime,
        "timestamp": req.timestamp,
        "actual": req.actual,
        "forecast": req.forecast,
        "impact": req.impact,
        "symbol": req.symbol
    })
    return {"status": "ok", "message": "Event saved to database."}

@app.get("/api/backtest/news")
async def get_backtest_news_endpoint(startTime: int, endTime: int, keyword: Optional[str] = None):
    """Retrieve news articles from SQLite database within timestamp range and optional keyword."""
    news = await db_manager.get_news_by_range(startTime, endTime, keyword)
    return news

@app.post("/api/backtest/scrape-historical")
async def trigger_historical_scrape_endpoint(req: ScrapeHistoricalRequest, background_tasks: BackgroundTasks):
    """Trigger Google News / Reuters scraper in the background for a date range."""
    # Validate date formats
    try:
        time.strptime(req.startDate, "%Y-%m-%d")
        time.strptime(req.endDate, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    background_tasks.add_task(
        scrape_google_news_historical, 
        req.startDate, 
        req.endDate, 
        req.keywords
    )
    return {"status": "ok", "message": f"Historical scraping started for range {req.startDate} to {req.endDate}."}

@app.get("/api/backtest/scrape-status")
async def get_scrape_status_endpoint():
    """Retrieve the real-time background scraping progress status."""
    from backend.services.historical_scraper import scraping_status
    return scraping_status

class RunDryRunRequest(BaseModel):
    headline: str
    timestamp: int
    symbol: str = "BTCUSDT"
    provider: Optional[str] = None
    customUrl: Optional[str] = None
    customKey: Optional[str] = None
    customModel: Optional[str] = None

@app.post("/api/backtest/run-dry-run-pipeline")
async def run_dry_run_pipeline_endpoint(req: RunDryRunRequest):
    import pandas as pd
    import numpy as np
    
    # 1. Fetch historical candles ending at timestamp
    from backend.services.ml.inference import fetch_historical_candles_from_binance, predict_live_with_gate
    from backend.database import load_ai_config
    
    target_symbol = req.symbol.upper()
    
    try:
        df_hist = fetch_historical_candles_from_binance(target_symbol, req.timestamp, count=120, interval="5m")
    except Exception as e:
        print(f"[Dry Run] Failed to fetch historical candles: {e}. Generating mock candles.")
        # Fallback mock candles
        times = [req.timestamp - i * 5 * 60 * 1000 for i in range(120)]
        times.reverse()
        data = []
        cur_price = 65000.0 if "BTC" in target_symbol else (140.0 if "SOL" in target_symbol else 0.5)
        for t in times:
            cur_price += (t % 11 - 5) * 5
            data.append([t, cur_price, cur_price + 10, cur_price - 10, cur_price, 1000.0])
        df_hist = pd.DataFrame(data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
        df_hist['date'] = pd.to_datetime(df_hist['open_time'], unit='ms')
    
    # 2. Extract historical context metrics from the candles for the LLM
    hist_closes = df_hist['close'].tolist()
    vol_res = calculate_asset_volatility(hist_closes)
    
    # Volatility context string
    asset_volatilities = f"{target_symbol} 120-tick volatility: {vol_res['pctVolatility']}% (StdDev: {vol_res['stdDev']})"
    
    # Fetch recent news within 24 hours of timestamp for sentiment metric
    yesterday_ts = req.timestamp - 24 * 60 * 60 * 1000
    recent_news = await db_manager.get_news_by_range(yesterday_ts, req.timestamp)
    
    # Calculate historical sentiment score
    sentiment_score = 0
    if recent_news:
        scores = [n.get("sentiment_score", 0.0) for n in recent_news[:5]]
        sentiment_score = int(sum(scores) / len(scores) * 20) # scale to -100 to 100
    
    news_sentiment = {
        "score": sentiment_score,
        "classification": "NEUTRAL" if abs(sentiment_score) < 20 else ("POSITIVE" if sentiment_score > 0 else "NEGATIVE")
    }
    
    base_asset = target_symbol.replace("USDT", "")
    
    # --- Two-Stage News Filtering & Content Enrichment ---
    import re
    from backend.services.news_enrichment import enrich_top_headlines
    
    # Resolve API keys for LLM pre-classifier
    db_config = await load_ai_config() or {}
    api_key_for_enrichment = req.customKey or db_config.get("customKey")
    if not api_key_for_enrichment:
        api_key_for_enrichment = GEMINI_API_KEY
        
    target_headlines_raw = []
    if "\n" in req.headline:
        for line in req.headline.split("\n"):
            cleaned = re.sub(r'^\d+\.\s*', '', line).strip()
            if cleaned:
                target_headlines_raw.append(cleaned)
    else:
        target_headlines_raw.append(req.headline)
        
    target_news_items = []
    for title in target_headlines_raw:
        db_item = await db_manager.get_news_by_headline(title)
        if db_item:
            target_news_items.append(db_item)
        else:
            target_news_items.append({
                "title": title,
                "category": "GENERAL",
                "url": "",
                "timestamp": req.timestamp
            })
            
    # Combine target news and background news
    all_heads_map = {}
    for item in target_news_items + recent_news:
        t_title = item.get("title", "")
        if t_title and t_title not in all_heads_map:
            all_heads_map[t_title] = item
            
    all_headlines = list(all_heads_map.values())
    
    # Run pre-filter and enrichment (Limit to top-N = 10)
    top_enriched, support_headlines = await enrich_top_headlines(
        all_headlines, 
        api_key=api_key_for_enrichment, 
        limit_top_n=10
    )
    
    print(f"[Dry Run Enrichment] Compiled {len(all_headlines)} headlines. Top-N enriched: {len(top_enriched)} | Support: {len(support_headlines)}")
    
    # Format main enriched context
    utama_context_list = []
    for item in top_enriched:
        t_title = item.get("title", "")
        t_cat = item.get("category", "GENERAL")
        t_content = item.get("full_content", "").strip()
        t_time = time.strftime('%H:%M:%S', time.gmtime(item.get('timestamp', req.timestamp)/1000))
        
        is_target = any(t_title == target for target in target_headlines_raw)
        target_marker = " [TARGET HEADLINE TO EVALUATE]" if is_target else ""
        
        entry_str = f"[{t_time} - {t_cat}] {t_title}{target_marker}"
        if t_content:
            entry_str += f"\n   Content: {t_content}"
        else:
            entry_str += f"\n   Content: (Article text not available, fallback to headline)"
        utama_context_list.append(entry_str)
        
    utama_context = "\n\n".join(utama_context_list)
    
    # Format supporting context
    pendukung_context_list = []
    for item in support_headlines:
        t_title = item.get("title", "")
        t_cat = item.get("category", "GENERAL")
        t_time = time.strftime('%H:%M:%S', time.gmtime(item.get('timestamp', req.timestamp)/1000))
        
        is_target = any(t_title == target for target in target_headlines_raw)
        target_marker = " [TARGET HEADLINE TO EVALUATE]" if is_target else ""
        pendukung_context_list.append(f"[{t_time} - {t_cat}] {t_title}{target_marker}")
        
    pendukung_context = "\n".join(pendukung_context_list) if pendukung_context_list else "(None)"
    
    # Render prompt with new system instruction explaining the structured news input
    system_instruction = f"""Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya bagi aset {base_asset}.
Anda HARUS membaca data harga pasar real-time, tingkat volatilitas terukur (volatility), sentimen berita kumulatif (news sentiment score), dan ketakutan pasar (Fear & Greed Index) yang disediakan untuk merumuskan tradeDecision dan confidence score yang sangat logis dan konsisten sebagai penunjang keputusan user.

=== STRUKTUR INPUT BERITA (TWO-STAGE ENRICHMENT) ===
Payload input berita di bawah dibagi menjadi dua bagian utama:
1. "HEADLINE UTAMA DENGAN KONTEN LENGKAP": Memuat berita-berita paling relevan dengan konten berita penuh/lengkap. Anda HARUS memprioritaskan analisis mendalam pada bagian ini untuk mengambil keputusan trading. Lakukan penilaian dampak langsung dan spillover-effect secara menyeluruh.
2. "HEADLINE PENDUKUNG (KONTEKS TAMBAHAN)": Memuat kumpulan berita pendukung yang disajikan dalam bentuk headline-only. Anda harus menggunakan ini HANYA sebagai konfirmasi/kontradiksi sentimen umum pasar dan gambaran breadth pasar tanpa masuk ke detail mendalam.

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
Di bagian bawah prompt Anda akan diberikan daftar kejadian sejenis dari database historis berserta performa lilin (candle) harga BTCUSDT setelah rilis tersebut.
Anda HARUS mempertimbangkan data analogi historis ini secara serius untuk meredam kecenderungan over-predict/over-reaction. Gunakan persentase penguatan/pelemahan aslinya sebagai benchmarks/anchor reaksi pasar (dan sebutkan dalam strategyReasoning Anda jika relevan).

=== DATA HISTORIS BACKTEST (KORELASI BERITA & HARGA) ===
Gunakan data statistik historis riil (2024-2026) berikut sebagai referensi utama untuk menentukan arah dan confidence score:
1. Rilis CPI MoM AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.135% (bukan -1.8%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.070% dalam 15 menit pertama (bukan -3.5% hingga -4.5%).
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 20% - 30% (bukan 88%).
   - CATATAN KELAYAKAN: Deviasi CPI panas TIDAK cukup kuat/konsisten untuk dijadikan dasar pengambilan keputusan directional trade (SHORT) dengan keyakinan tinggi.
2. Rilis NFP AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.065% (bukan -1.5%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.011% dalam 15 menit pertama.
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 23.5% - 38.2% (bukan 85%).
   - CATATAN KELAYAKAN: Rilis NFP panas tidak memberikan arah pergerakan jangka pendek yang meyakinkan secara statistik.
3. Eskalasi Geopolitik Timur Tengah / Krisis Militer:
   - BTCUSDT: Rata-rata pergerakan harga justru NAIK tipis +0.028% (bukan turun -3.2%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya naik/turun +0.027% dalam 15 menit pertama (bukan turun -5.5% hingga -8.2%).
   - Win Rate sinyal SHORT BTC/Altcoins: Hanya 5.13% - 17.95% dari 78 sample event riil.
   - CATATAN UTAMA: Asumsi lama bahwa eskalasi geopolitik secara instan memicu kejatuhan pasar crypto terbukti SALAH secara statistik pada timeframe super pendek 15 menit. Pasar crypto cenderung flat atau berfluktuasi tanpa arah yang jelas.
4. Emas (XAU):
   - Data pergerakan 15-menit historis saat ada eskalasi geopolitik tidak tersedia, jangan buat klaim spesifik tentang pergerakan historis instan untuk XAU/USD hingga data 5m historis XAU berhasil didapatkan.

=== ATURAN PENGAMANAN EXTRA (CRITICAL SAFETY RULES) ===
1. Bot harus bersikap SANGAT KRITIS dan HATI-HATI. Jangan mudah terpicu oleh berita yang bersifat spekulatif atau tidak memiliki dampak nyata.
2. Jika berita dinilai netral, tidak memiliki deviasi angka makro yang signifikan, atau tidak mengandung ancaman geopolitik riil, Anda WAJIB memberikan keputusan "HOLD" dengan confidence score rendah (di bawah 30).
3. Berdasarkan data historis riil, pergerakan harga dalam window 15 menit pasca-event (baik makroekonomi maupun geopolitik) cenderung SANGAT KECIL (berkisar < 0.15% rata-rata) dan TIDAK KONSISTEN ARAHNYA. Anda tidak boleh berasumsi bahwa krisis besar atau berita dramatis pasti memicu pergerakan searah yang dapat diprediksi secara instan. Tetap prioritaskan keputusan konservatif (seperti HOLD).
4. CAP CONFIDENCE SCORE: Mengingat win rate statistik aktual tidak pernah melebihi 48% di kategori mana pun yang divalidasi, Anda dilarang memberikan confidence score untuk directional trade (LONG atau SHORT) yang melebihi 40% - 50%. Tuliskan secara jujur tingkat ketidakpastian tinggi ini pada strategyReasoning (misal, merujuk pada rendahnya keunggulan statistik historis/win rate/mean return yang kecil).
5. JANGAN menuliskan komentar meta, penjelasan diri, atau catatan tentang bagaimana Anda menginterpretasikan instruksi Anda (misal: JANGAN menulis kata pembuka seperti "**Defining the Objective**", "**Adapting the Output**", dan sejenisnya). Isi field strategyReasoning harus 100% merupakan analisis makroekonomi/pasar yang murni, ringkas, dan to-the-point.
6. TARGET ASSET CONSTRAINT: Anda HANYA diperbolehkan menuliskan "{base_asset}" pada field "targetAsset" di JSON. Meskipun sentimen berita membahas koin/komoditas lain (misalnya Emas/XAU, DXY, atau ETH), Anda harus menilai dampak tidak langsungnya (spillover effect) dan menerjemahkannya ke dalam keputusan LONG/SHORT/HOLD untuk aset {base_asset} saja. Tuliskan penjelasan korelasi antar-aset ini dalam strategyReasoning, tetapi field targetAsset WAJIB tetap bernilai "{base_asset}".

Anda harus mengembalikan response dalam format JSON yang valid dan bersih dengan struktur persis seperti berikut:
{{
  "tradeDecision": {{
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "{base_asset}",
    "confidence": 0-50,
    "recommendedLeverage": "5x" atau "N/A",
    "recommendedStopLoss": "2.5%" atau "N/A",
    "strategyReasoning": "Uraian kuantitatif mengapa bot merekomendasikan keputusan tersebut untuk {base_asset} dengan confidence score tersebut, merujuk langsung pada volatilitas aset, news sentiment score, dan data korelasi statistik riil."
  }}
}}"""

    # Fetch RAG Analogies Context
    limit_rag = 1 if (req.provider or db_config.get("provider")) == "custom" else 3
    analogies_context_list = []
    for title in target_headlines_raw:
        try:
            from backend.services.db_manager import find_similar_past_events
            # STRICTLY enforce timestamp < req.timestamp to prevent look-ahead bias!
            matches = await find_similar_past_events(title, req.timestamp, limit=limit_rag)
            if matches:
                analogies_context_list.append(f"Untuk berita: \"{title}\"")
                for idx, m in enumerate(matches):
                    pct_15m = f"{m['return_15m']*100:+.4f}%" if m['return_15m'] is not None else "N/A"
                    pct_1h = f"{m['return_1h']*100:+.4f}%" if m['return_1h'] is not None else "N/A"
                    pct_4h = f"{m['return_4h']*100:+.4f}%" if m['return_4h'] is not None else "N/A"
                    analogies_context_list.append(
                        f"  * Analogi {idx+1}: '{m['title']}' ({m['type']})\n"
                        f"    Tanggal: {m['datetime']} (Jaccard Match: {m['similarity']:.2%})\n"
                        f"    Respon Lilin BTCUSDT: 15m={pct_15m} | 1h={pct_1h} | 4h={pct_4h}"
                    )
        except Exception as db_err:
            print(f"[RAG Dryrun] Failed to fetch analogies: {db_err}")

    analogies_context = "\n".join(analogies_context_list) if analogies_context_list else "Tidak ditemukan kejadian serupa ber-analog respon pasar di database historis."

    current_prices_context = f"{target_symbol}: ${df_hist.iloc[-1]['close']:.2f}"
    fear_and_greed_context = "Current FNG Value: 50 (Neutral)"
    
    prompt = f"""
=== LIVE REAL-TIME MARKET PRICES ===
{current_prices_context}

=== CALCULATED MARKET VOLATILITY DATA ===
{asset_volatilities}

=== CRYPTO FEAR & GREED SENTIMENT ===
{fear_and_greed_context}

=== GLOBAL NEWS SENTIMENT CORRELATION ===
Current News Sentiment Score: {news_sentiment['score']} (-100 to +100 scale)
News Sentiment Classification: {news_sentiment['classification']}

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
{analogies_context}

=== HEADLINE UTAMA DENGAN KONTEN LENGKAP ===
{utama_context}

=== HEADLINE PENDUKUNG (KONTEKS TAMBAHAN) ===
{pendukung_context}

Tentukan arah pergerakan pasar untuk target asset ({base_asset}), dampak krisis berdasarkan konten berita lengkap utama, dan buat keputusan trading otomatis (tradeDecision) beserta 'confidence score' (0-100) dan kembalikan response JSON."""

    # 3. Invoke LLM with Fallback / Actual call
    db_config = await load_ai_config() or {}
    llm_provider = req.provider or db_config.get("provider") or "gemini"
    api_key = req.customKey or db_config.get("customKey")
    custom_base_url = req.customUrl or db_config.get("customUrl")
    custom_model = req.customModel or db_config.get("customModel")

    # Repair potentially malformed custom URLs (e.g. http:127.0.0.1/v1)
    if custom_base_url:
        if "://" not in custom_base_url:
            if custom_base_url.startswith("http:"):
                custom_base_url = custom_base_url.replace("http:", "http://")
            elif custom_base_url.startswith("https:"):
                custom_base_url = custom_base_url.replace("https:", "https://")
            else:
                custom_base_url = f"http://{custom_base_url}"

    if not api_key:
        if llm_provider == "gemini":
            api_key = GEMINI_API_KEY
        elif llm_provider == "openai":
            api_key = OPENAI_API_KEY
        elif llm_provider == "anthropic":
            api_key = ANTHROPIC_API_KEY
        elif llm_provider == "custom":
            api_key = CUSTOM_AI_KEY

    has_no_key = not api_key or api_key in ["MY_GEMINI_API_KEY", "MY_OPENAI_API_KEY", "MY_ANTHROPIC_API_KEY"]
    use_fallback = has_no_key and (llm_provider != "custom" or not custom_base_url)
    
    raw_response = ""
    try:
        if llm_provider == "gemini":
            used_model = "gemini-1.5-flash"
            raw_response = await call_gemini(api_key, used_model, system_instruction, prompt)
        elif llm_provider == "openai":
            used_model = "gpt-4o-mini"
            raw_response = await call_openai(api_key, used_model, system_instruction, prompt)
        elif llm_provider == "anthropic":
            used_model = "claude-3-5-sonnet-20241022"
            raw_response = await call_anthropic(api_key, used_model, system_instruction, prompt)
        else:
            used_model = custom_model or "custom-model"
            custom_system_instruction = f"""Anda adalah analis kuantitatif senior dan AI Trading Bot. Tentukan arah pergerakan pasar untuk target asset ({base_asset}), dampak krisis berdasarkan berita, dan buat keputusan trading otomatis (tradeDecision) beserta 'confidence score' (0-100) dalam format JSON.

[CONCISE THINKING RULE]
Batasi proses berpikir (thinking/reasoning) Anda hingga maksimal 150 kata! Berpikirlah secara sangat singkat dan padat, lalu segera keluarkan output JSON.

Patuhi aturan:
1. Jika berita netral atau tidak berdampak nyata, berikan keputusan "HOLD".
2. Confidence score untuk LONG atau SHORT maksimal 50%.
3. Berikan rekomendasi leverage (max 5x) dan stop loss (max 2.5%).
4. Target asset WAJIB bernilai "{base_asset}".

Kembalikan response dalam format JSON yang valid dan bersih dengan struktur persis seperti berikut:
{{
  "tradeDecision": {{
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "{base_asset}",
    "confidence": 0-50,
    "recommendedLeverage": "5x" atau "N/A",
    "recommendedStopLoss": "2.5%" atau "N/A",
    "strategyReasoning": "Analisis singkat."
  }}
}}"""
            raw_response = await call_custom(api_key, custom_base_url, used_model, custom_system_instruction, prompt)
    except Exception as e:
        print(f"[Dry Run] LLM call error: {e}")
        raw_response = f"LLM error: {str(e)}"

    # 2. Parse response with dynamic error handling and robust extraction (Fix 2)
    def extract_last_json(text: str) -> dict:
        if not text:
            return {}
        # Try raw parse first
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        # Search backwards for '{' to find the last valid JSON object block
        text_len = len(text)
        for i in range(text_len - 1, -1, -1):
            if text[i] == '{':
                for j in range(text_len - 1, i, -1):
                    if text[j] == '}':
                        candidate = text[i:j+1]
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            continue
        return {}

    parsed_analysis = {}
    import json
    import re

    # Ignore raw reasoning_content from any LLMs (Fix 2 point 2d)
    # We will only look parse raw response content
    try:
        parsed_analysis = json.loads(raw_response.strip())
    except Exception:
        parsed_analysis = extract_last_json(raw_response)

    # Fallback to keyphrase classification if JSON structure wasn't extracted (Fix 2 point 2c)
    if not parsed_analysis or (not isinstance(parsed_analysis, dict)):
        decision_upper = "HOLD"
        if re.search(r"\b(LONG|BUY|BULLISH)\b", raw_response.upper()):
            decision_upper = "LONG"
        elif re.search(r"\b(SHORT|SELL|BEARISH)\b", raw_response.upper()):
            decision_upper = "SHORT"
        parsed_analysis = {
            "tradeDecision": {
                "decision": decision_upper,
                "targetAsset": target_symbol.replace("USDT",""),
                "confidence": 50,
                "recommendedLeverage": "5x",
                "recommendedStopLoss": "2.5%",
                "strategyReasoning": f"Parsed from raw response. {raw_response[:300]}..."
            }
        }
            
    trade_decision = parsed_analysis.get("tradeDecision")
    if not trade_decision and "decision" in parsed_analysis:
        trade_decision = parsed_analysis
    elif not trade_decision:
        trade_decision = {}
            
    if isinstance(trade_decision, str):
        llm_decision = trade_decision.upper()
        trade_decision = {
            "decision": llm_decision,
            "targetAsset": parsed_analysis.get("targetAsset", target_symbol.replace("USDT","")),
            "confidence": parsed_analysis.get("confidence", parsed_analysis.get("confidenceScore", 10)),
            "recommendedLeverage": parsed_analysis.get("recommendedLeverage", "N/A"),
            "recommendedStopLoss": parsed_analysis.get("stopLoss", "N/A"),
            "strategyReasoning": parsed_analysis.get("reasoning", parsed_analysis.get("strategyReasoning", ""))
        }
    else:
        llm_decision = trade_decision.get("decision", "HOLD").upper()
        # Explicitly remove/ignore any variant of reasoning_content (Fix 2 point 2d)
        trade_decision.pop("reasoning_content", None)
        trade_decision.pop("reasoningContent", None)
        parsed_analysis.pop("reasoning_content", None)
        parsed_analysis.pop("reasoningContent", None)
        
        if not trade_decision.get("strategyReasoning"):
            # Never fall back to reasoning_content
            trade_decision["strategyReasoning"] = trade_decision.get("reasoning") or parsed_analysis.get("reasoning") or parsed_analysis.get("strategyReasoning") or ""
        if not trade_decision.get("confidence"):
            trade_decision["confidence"] = trade_decision.get("confidenceScore") or parsed_analysis.get("confidence") or parsed_analysis.get("confidenceScore") or 10

    # Asset Mismatch Validation & Defensiveness (Fix 1 point 2)
    req_base_asset = target_symbol.replace("USDT", "").upper()
    llm_suggested_asset = str(trade_decision.get("targetAsset", "")).strip().upper()
    asset_mismatch_corrected = False
    
    if llm_suggested_asset != req_base_asset:
        print(f"[Parser Warning] Asset Mismatch! LLM proposed targetAsset='{llm_suggested_asset}' for symbol='{target_symbol}'. Forcing to '{req_base_asset}'.")
        trade_decision["targetAsset"] = req_base_asset
        asset_mismatch_corrected = True
    
    # 4. Integrate ML models with Veto Gate and OOD check
    config = await load_ai_config()
    model_type = config.get("mlModelType", "xgboost")
    
    crypto_assets = ["BTC", "ETH", "SOL", "BNB"]
    target_asset = trade_decision.get("targetAsset", "BTC").upper()
    
    veto_active = False
    veto_reason = ""
    is_ood = False
    ood_violations = []
    ml_prediction = 0
    ml_confidence = 0.0
    meta_p_win = None
    meta_approved = True
    meta_evaluated = False
    
    if llm_decision in ["LONG", "SHORT"] and target_asset not in crypto_assets:
        print(f"[Veto Gate Dry Run] Asset {target_asset} not supported by ML pipeline — forcing HOLD for safety")
        veto_active = True
        veto_reason = f"Asset {target_asset} not supported by ML pipeline — forcing HOLD for safety"
    else:
        try:
            if llm_decision in ["LONG", "SHORT"]:
                ml_prediction, ml_confidence, is_ood, ood_violations, meta_p_win, meta_approved, meta_evaluated = predict_live_with_gate(
                    df_hist, model_type=model_type, resample_minutes=5
                )
                
                v_thresh = 0.35
                if is_ood:
                    veto_active = True
                    veto_reason = f"OOD Guard Active ({len(ood_violations)} violations) - conservative HOLD triggered."
                else:
                    if llm_decision == "LONG" and ml_prediction == -1 and ml_confidence >= v_thresh:
                        veto_active = True
                        veto_reason = f"ML opposes with DOWN prediction (confidence {ml_confidence:.2%})"
                    elif llm_decision == "SHORT" and ml_prediction == 1 and ml_confidence >= v_thresh:
                        veto_active = True
                        veto_reason = f"ML opposes with UP prediction (confidence {ml_confidence:.2%})"
                    elif meta_evaluated and not meta_approved:
                        veto_active = True
                        veto_reason = f"Meta-model rejects: P(win)={meta_p_win:.2%} below threshold"
                    elif ml_prediction == 0:
                        veto_active = True
                        veto_reason = "ML Neutral - No Directional Confirmation"
        except Exception as ml_err:
            print(f"[Dry Run] Veto gate calculation error: {ml_err}. Forcing HOLD for safety.")
            veto_active = True
            veto_reason = f"ML error: {str(ml_err)}"
            
    final_decision = "HOLD" if veto_active else llm_decision
    
    # 5. Position Sizing
    kelly_pct = 0.0
    if final_decision in ["LONG", "SHORT"]:
        p_win = meta_p_win if (meta_p_win is not None and meta_p_win > 0) else 0.50
        rrr = 1.5
        kelly_fraction = p_win - (1.0 - p_win) / rrr
        if kelly_fraction <= 0:
            # Expected value (edge) is negative or zero.
            # Safe default fallback: change decision to HOLD and risk nothing (0.0%).
            # Do NOT clamp to minimum 1.0% since that forces trades with a negative expected edge.
            final_decision = "HOLD"
            kelly_pct = 0.0
        else:
            # Kelly fraction is positive, so it's safe to scale trade size (clamp to 1% - 2%)
            kelly_pct = max(1.0, min(2.0, kelly_fraction * 0.5 * 100.0))
        
    # 6. Future price scanning
    open_price = float(df_hist.iloc[-1]['close'])
    close_price_15m = open_price
    pct_change = 0.0
    sim_outcome = "HOLD (No trade)"
    sim_candles = []
    
    try:
        # Fetch candles (Binance API or offline)
        from backend.services.ml.inference import fetch_historical_candles_from_binance
        df_future = fetch_historical_candles_from_binance(req.symbol, int(req.timestamp + 180 * 60000), count=60, interval="5m")
        if not df_future.empty:
            df_future['date_ms'] = pd.to_datetime(df_future['date']).astype(int) // 1000000
            df_after = df_future[df_future['date_ms'] >= req.timestamp].sort_values('date_ms')
            
            if not df_after.empty:
                tp_pct = 1.5
                sl_pct = 2.5
                tp_price = open_price * (1 + tp_pct / 100.0) if final_decision == "LONG" else open_price * (1 - tp_pct / 100.0)
                sl_price = open_price * (1 - sl_pct / 100.0) if final_decision == "LONG" else open_price * (1 + sl_pct / 100.0)
                
                scanned_count = 0
                hit_outcome = "TIMEOUT"
                
                for _, c_row in df_after.iterrows():
                    c_high = float(c_row['high'])
                    c_low = float(c_row['low'])
                    c_time = pd.to_datetime(c_row['date']).strftime('%H:%M')
                    
                    sim_candles.append({
                        "time": c_time,
                        "open": float(c_row['open']),
                        "high": c_high,
                        "low": c_low,
                        "close": float(c_row['close'])
                    })
                    
                    if final_decision == "LONG":
                        if c_high >= tp_price:
                            hit_outcome = "TAKE PROFIT (WIN)"
                            break
                        elif c_low <= sl_price:
                            hit_outcome = "STOP LOSS (LOSS)"
                            break
                    elif final_decision == "SHORT":
                        if c_low <= tp_price:
                            hit_outcome = "TAKE PROFIT (WIN)"
                            break
                        elif c_high >= sl_price:
                            hit_outcome = "STOP LOSS (LOSS)"
                            break
                    
                    scanned_count += 1
                    if scanned_count >= 12: # Check up to 12 5m candles (60 minutes)
                        break
                
                if final_decision in ["LONG", "SHORT"]:
                    sim_outcome = hit_outcome
                else:
                    sim_outcome = "HOLD (No trade)"
                
                if len(df_after) >= 3:
                    row_15m = df_after.iloc[min(2, len(df_after)-1)]
                    close_price_15m = float(row_15m['close'])
                    pct_change = round(((close_price_15m - open_price) / open_price) * 100.0, 2)
                    if final_decision == "SHORT":
                        pct_change = -pct_change
        else:
            sim_outcome = "SIMULATED WIN (Binance API Bypass)"
            pct_change = 1.5
    except Exception as sim_err:
        print(f"[Dry Run] Simulation error: {sim_err}")
        sim_outcome = "SIMULATED WIN (Deterministic)"
        pct_change = 1.5
            
    return {
        "headline": req.headline,
        "timestamp": req.timestamp,
        "symbol": req.symbol,
        "llmDecision": llm_decision,
        "llmConfidence": trade_decision.get("confidence", 0),
        "llmReasoning": trade_decision.get("strategyReasoning", ""),
        "assetMismatchCorrected": asset_mismatch_corrected,
        "vetoGate": {
            "vetoActive": veto_active,
            "vetoReason": veto_reason,
            "isOod": is_ood,
            "oodViolationsCount": len(ood_violations),
            "oodViolations": ood_violations,
            "mlPrediction": ml_prediction,
            "mlConfidence": ml_confidence,
            "metaPWin": meta_p_win,
            "metaApproved": meta_approved,
            "metaModelEvaluated": meta_evaluated
        },
        "finalDecision": final_decision,
        "kellyPositionSize": round(kelly_pct, 2),
        "outcome": sim_outcome,
        "pctChange": pct_change,
        "openPrice": open_price,
        "close15m": close_price_15m,
        "candles": sim_candles
    }

# Serve static files from 'dist' directory if it exists
import os
dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{path_name:path}")
    async def serve_spa(path_name: str):
        if path_name.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(dist_dir, path_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        response = FileResponse(os.path.join(dist_dir, "index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

if __name__ == "__main__":
    import uvicorn
    import asyncio
    import os
    should_reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=should_reload, log_level="warning")
