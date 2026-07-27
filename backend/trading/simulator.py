"""Trading simulation logic extracted from main.py."""
import time
import asyncio
from typing import Dict, Any

from backend.core.logger import logger
from backend.helpers.utils import get_asset_current_price, is_headline_relevant, _calculate_risk_parameters
from backend.services.news import news_feed, news_feed_lock, analyze_sentiment


async def _execute_simulated_trade(headline, target_asset, decision, confidence, strategy, trade_decision, correlation_log, veto_active, bot_settings, threshold):
    from backend.sentix_adapter import sentix_state, _save_sentix_db
    
    live_price = get_asset_current_price(target_asset)
    if not live_price or live_price <= 0.0:
        logger.error(f"[Simulator] Failed to resolve current live price for asset {target_asset}. Aborting trade.")
        return

    # Adaptive Microstructure Slippage Model (Institusional Market Impact)
    # Estimate slippage based on leverage & volatility baseline (0.01% - 0.05% slippage friction)
    lev_mult = int(bot_settings.get("leverage", 5))
    slippage_pct = min(0.05, 0.005 * (lev_mult / 5.0))
    if decision == "LONG":
        executed_entry_price = round(live_price * (1.0 + slippage_pct / 100.0), 4)
    elif decision == "SHORT":
        executed_entry_price = round(live_price * (1.0 - slippage_pct / 100.0), 4)
    else:
        executed_entry_price = live_price
        
    symbol_usdt = f"{target_asset}USDT"
    
    log_action = "BUY" if decision == "LONG" else "SELL" if decision == "SHORT" else "HOLD"
    price_fmt = f"${live_price:,.4f}" if target_asset in ["DOGE", "ADA", "XRP"] else f"${live_price:,.2f}"
    
    log_entry = {
        "id": f"log-bot-{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "action": log_action,
        "symbol": symbol_usdt,
        "price": live_price,
        "confidence": confidence,
        "message": f"🤖 [AI BOT Auto ({strategy})]: Menganalisis {target_asset} @ {price_fmt}. Keputusan: {decision} ({confidence}%). Alasan: {trade_decision.get('strategyReasoning', '')}{correlation_log}"
    }
    
    if "aiBotLogs" not in sentix_state: sentix_state["aiBotLogs"] = []
    
    sentiment_threshold = float(bot_settings.get("sentimentThreshold", 0.0))
    if decision in ["LONG", "SHORT"] and (confidence / 100.0) < sentiment_threshold:
        decision, log_entry["action"] = "HOLD", "HOLD"
        log_entry["message"] += f" [Veto: Sentimen Aktual {confidence/100.0:.2f} < Batas {sentiment_threshold}]"

    sentix_state["aiBotLogs"].insert(0, log_entry)
    sentix_state["aiBotLogs"] = sentix_state["aiBotLogs"][:100]
    
    # NOTE: news_feed insert is handled by analyze_ai() in routes/ai.py — skipping duplicate insert here
    
    risk = _calculate_risk_parameters(bot_settings, live_price, decision, strategy, target_asset=target_asset)
    
    if decision in ["LONG", "SHORT"] and not veto_active and confidence >= threshold:
        margin = risk["margin"]
        if strategy == "MARTINGALE":
            closed_trades = sorted([t for t in sentix_state.get("trades", []) if t.get("status") == "CLOSED"], key=lambda x: x.get("closeTime", 0) or x.get("exitTimestamp", 0) or 0, reverse=True)
            if closed_trades and (closed_trades[0].get("pnl", 0.0) or 0.0) < 0.0:
                margin *= 2.0
                log_entry["message"] += f" [Martingale Double Active: ${margin}]"

        def add_sentix_trade(trade_type, sl_val, tp_val, active_margin):
            qty = (active_margin * risk["lev"]) / live_price
            if "trades" not in sentix_state: sentix_state["trades"] = []
            sentix_state["trades"].append({
                "id": f"trade-bot-{trade_type.lower()}-{int(time.time() * 1000)}",
                "symbol": symbol_usdt, "type": trade_type, "size": round(qty, 6), "leverage": risk["lev"],
                "entryPrice": live_price, "exitPrice": None, "pnl": None, "sl": round(sl_val, 2), "tp": round(tp_val, 2),
                "trailingStopPct": None, "status": "OPEN", "timestamp": int(time.time() * 1000), "exitTimestamp": None,
                "reason": f"AI_BOT_{strategy}"
            })
            sentix_state["portfolio"]["balanceUSD"] = round(sentix_state["portfolio"]["balanceUSD"] - active_margin, 2)
            
        if strategy == "HEDGING":
            has_l = any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt and t.get("type") == "BUY" for t in sentix_state.get("trades", []))
            has_s = any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt and t.get("type") == "SELL" for t in sentix_state.get("trades", []))
            if not has_l: add_sentix_trade("BUY", risk["long_sl"], risk["long_tp"], margin)
            if not has_s: add_sentix_trade("SELL", risk["short_sl"], risk["short_tp"], margin)
        else:
            if not any(t.get("status") == "OPEN" and t.get("symbol") == symbol_usdt for t in sentix_state.get("trades", [])):
                add_sentix_trade("BUY" if decision == "LONG" else "SELL", risk["sl_price"], risk["tp_price"], margin)
                
    _save_sentix_db()
    
    if decision in ["LONG", "SHORT"] and not veto_active and confidence >= threshold:
        from backend.database import db_lock, read_database_async, write_database_async
        async with db_lock:
            db = await read_database_async()
            existing_trades = db.setdefault("savedTrades", [])
            
            def add_db_trade(trade_dec, sl_val, tp_val):
                sim = {
                    "id": f"trade-{trade_dec.lower()}-{int(time.time() * 1000)}", "timestamp": int(time.time() * 1000),
                    "decision": trade_dec, "targetAsset": target_asset, "confidence": confidence,
                    "recommendedLeverage": f"{risk['lev']}x", "recommendedStopLoss": f"{risk['sl_pct_raw']}%", "recommendedTakeProfit": f"{risk['tp_pct_raw']}%",
                    "strategyReasoning": f"[{strategy} Strategy] {trade_decision.get('strategyReasoning', '')}",
                    "status": "OPEN", "entryPrice": live_price, "currentPrice": live_price, "exitPrice": None, "closeTime": None,
                    "closeReason": None, "pnl": 0.0, "headline": headline, "type": "SIMULATED", "margin": risk["margin"]
                }
                if strategy == "HEDGING":
                    sim["strategyReasoning"] = f"[HEDGING Strategy] Dual directional entry. {trade_decision.get('strategyReasoning', '')}"
                db["savedTrades"].insert(0, sim)
                db["savedTrades"] = db["savedTrades"][:100]
                
                # Send telegram alert ONLY when trade is successfully added to the database
                from backend.services.telegram_client import send_telegram_alert
                asyncio.create_task(send_telegram_alert(
                    f"🚀 *Simulated Trade Opened* 🚀\n\n"
                    f"*Asset*: {target_asset}\n"
                    f"*Action*: {trade_dec}\n"
                    f"*Entry Price*: ${live_price}\n"
                    f"*Confidence*: {confidence}%\n"
                    f"*SL*: {risk['sl_pct_raw']}% | *TP*: {risk['tp_pct_raw']}%\n"
                    f"*Reason*: {trade_decision.get('strategyReasoning', '')}"
                ))

            if strategy == "HEDGING":
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "LONG" for t in existing_trades): add_db_trade("LONG", risk["long_sl"], risk["long_tp"])
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "SHORT" for t in existing_trades): add_db_trade("SHORT", risk["short_sl"], risk["short_tp"])
            else:
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset for t in existing_trades):
                    add_db_trade(decision, risk["sl_price"], risk["tp_price"])
            await write_database_async(db)
            
        # Removed old duplicate send_telegram_alert call that was placed here outside db checks
        pass


async def trigger_automated_trade_sim(item: Dict[str, Any], config: Dict[str, Any], force: bool = False):
    """Trigger simulated trade in paper trading mode."""
    try:
        headline = item["title"]
        source = item.get("source", "Unknown")
        
        from backend.helpers.utils import is_headline_processed, mark_headline_processed
        if not force and is_headline_processed(headline):
            logger.info(f"[Sim Trading] Headline already processed, skipping: {headline}")
            return
            
        mark_headline_processed(headline)
        
        if not is_headline_relevant(headline, source):
            logger.info(f"[Sim Trading] Skipping LLM for irrelevant headline: {headline}")
            sentiment_res = analyze_sentiment(headline)
            from backend.services.news import news_feed_lock
            async with news_feed_lock:
                news_feed.insert(0, {
                    "id": f"n-{int(time.time() * 1000)}", "time": time.strftime("%H:%M:%S"),
                    "headline": headline, "category": "GENERAL", "impact": "LOW", "source": source,
                    "details": f"Scraped from {source}. Sentiment score: {sentiment_res['score']}. Bypassed AI Bot Trade Analysis.",
                    "forecast": item.get("forecast", ""), "previous": item.get("previous", ""),
                    "isTriggeredShort": False, "isTriggeredGold": False, "summaryId": f"Scraped news. Bypassed AI Bot."
                })
                if len(news_feed) > 50: news_feed.pop()
            return
            
        from backend.sentix_adapter import sentix_state
        bot_settings = sentix_state.get("aiBotSettings", {})
        
        # Import _evaluate_llm_trade_signal from bot module
        from backend.trading.bot import _evaluate_llm_trade_signal
        
        # Check if strategy is SCALPING to bypass LLM logic completely
        if bot_settings.get("strategy", "CONSERVATIVE").upper() == "SCALPING":
            from backend.services.ml.inference import fetch_recent_candles, predict_live_with_gate
            target_asset = bot_settings.get("symbol", "BTCUSDT").replace("USDT", "")
            df_recent = await fetch_recent_candles(target_asset, count=120, interval="5m")
            
            model_type = bot_settings.get("modelType", config.get("mlModelType", "lightgbm"))
            resample_min = bot_settings.get("timeframeMinutes", 5)
            
            ml_pred, ml_conf, is_ood, ood_violations, meta_p_win, meta_approved, meta_evaluated = predict_live_with_gate(
                df_recent, model_type=model_type, resample_minutes=resample_min
            )
            
            decision = "LONG" if ml_pred == 1 else "SHORT" if ml_pred == -1 else "HOLD"
            confidence = int(ml_conf * 100)
            strategy = "SCALPING"
            trade_decision = {
                "decision": decision,
                "confidence": confidence,
                "strategyReasoning": f"Eksekusi Scalping murni berbasis Technical Machine Learning model {model_type.upper()} (LLM Bypassed)."
            }
            veto_mode = bot_settings.get("vetoGateMode", "AUTO").upper()
            if veto_mode == "ON":
                veto_active = True
                correlation_log = " | VETO GATE FORCED ON BY MASTER OVERRIDE"
            elif veto_mode == "OFF":
                veto_active = False
                correlation_log = " | SCALPING ML BYPASS ACTIVE (FORCE OFF)"
            else: # AUTO: SCALPING bypasses Veto Gate by default behavior for speed
                veto_active = False
                correlation_log = " | SCALPING ML BYPASS ACTIVE (AUTO)"
        else:
            target_asset, decision, confidence, strategy, trade_decision, veto_active, correlation_log = await _evaluate_llm_trade_signal(headline, item, config, bot_settings)
            
        threshold = bot_settings.get("minConfidence", config.get("confidenceThreshold", 75))
        
        await _execute_simulated_trade(headline, target_asset, decision, confidence, strategy, trade_decision, correlation_log, veto_active, bot_settings, threshold)
        
    except Exception as err:
        logger.error(f"[Sim Trading] Error running automated trade: {err}")
