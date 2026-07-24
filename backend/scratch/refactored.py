async def _evaluate_llm_trade_signal(headline, item, config, bot_settings):
    from backend.services.ai import AIAnalyzeRequest, analyze_ai
    from backend.services.market import assets, calculate_asset_beta
    active_symbol = bot_settings.get("symbol", "BTCUSDT")
    active_asset = active_symbol.upper().replace("USDT", "")
    
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
    
    trade_decision["targetAsset"] = active_asset
    decision = trade_decision.get("decision", "HOLD")
    confidence = trade_decision.get("confidence", 0)
    
    correlation_log = ""
    if active_asset != "BTC":
        hist_target = []
        hist_btc = []
        for a in assets:
            if a["symbol"].upper() == active_asset: hist_target = a["history"]
            elif a["symbol"].upper() == "BTC": hist_btc = a["history"]
                
        if hist_target and hist_btc:
            stats = calculate_asset_beta(hist_target, hist_btc)
            r_val, beta_val = stats["correlation"], stats["beta"]
            
            is_general_news = any(k in headline.lower() for k in ["btc", "bitcoin", "market", "crypto", "fed", "inflation", "cpi", "nfp", "sec", "etf", "induk", "receh", "meme"])
            if is_general_news and abs(r_val) >= 0.45:
                btc_expected_pct = next((float(i.get("percentage", 0.0)) for i in analysis.get("assetsImpact", []) if i.get("symbol") == "BTC"), 0.0)
                if btc_expected_pct == 0.0:
                    sentiment = analysis.get("sentiment", "NEUTRAL")
                    if sentiment == "POSITIVE": btc_expected_pct = 0.15
                    elif sentiment == "NEGATIVE": btc_expected_pct = -0.15
                    elif sentiment == "CRITICAL": btc_expected_pct = -0.30
                
                target_expected_pct = round(btc_expected_pct * beta_val, 4)
                if target_expected_pct > 0.02:
                    decision, confidence = "LONG", int(min(95, max(30, confidence * abs(r_val))))
                elif target_expected_pct < -0.02:
                    decision, confidence = "SHORT", int(min(95, max(30, confidence * abs(r_val))))
                else:
                    decision, confidence = "HOLD", int(confidence * (1 - abs(r_val)))
                    
                trade_decision["decision"] = decision
                trade_decision["confidence"] = confidence
                correlation_log = f" | Translasi Berita BTC: r={r_val:+.2f}, β={beta_val:+.2f}, Dampak BTC ({btc_expected_pct:+.2f}%) -> {active_asset} ({target_expected_pct:+.2f}%)"

    strategy = bot_settings.get("strategy", "CONSERVATIVE").upper()
    bypass_veto = strategy in ["AGGRESSIVE", "SCALPING", "HEDGING"]
    veto_active = False if bypass_veto else veto_gate.get("vetoActive", False)
    
    return active_asset, decision, confidence, strategy, trade_decision, veto_active, correlation_log

def _calculate_risk_parameters(bot_settings, live_price, decision, strategy):
    lev_val = int(bot_settings.get("leverage", 10))
    sl_pct = float(bot_settings.get("stopLossPct", 1.5)) * float(bot_settings.get("slMultiplier", 1.0))
    tp_pct = float(bot_settings.get("takeProfitPct", 3.0)) * float(bot_settings.get("tpMultiplier", 1.0))
    margin = float(bot_settings.get("allocationPerTrade", 1000.0))
    
    if strategy == "HEDGING":
        h_sl_pct, h_tp_pct = 1.5, 3.0
        return {
            "lev": lev_val, "margin": margin,
            "long_sl": live_price * (1 - h_sl_pct / 100), "long_tp": live_price * (1 + h_tp_pct / 100),
            "short_sl": live_price * (1 + h_sl_pct / 100), "short_tp": live_price * (1 - h_tp_pct / 100),
            "sl_pct_raw": h_sl_pct, "tp_pct_raw": h_tp_pct
        }
    
    sl_price = live_price * (1 - sl_pct / 100) if decision == "LONG" else live_price * (1 + sl_pct / 100)
    tp_price = live_price * (1 + tp_pct / 100) if decision == "LONG" else live_price * (1 - tp_pct / 100)
    return {"lev": lev_val, "margin": margin, "sl_price": sl_price, "tp_price": tp_price, "sl_pct_raw": sl_pct, "tp_pct_raw": tp_pct}

async def _execute_simulated_trade(headline, target_asset, decision, confidence, strategy, trade_decision, correlation_log, veto_active, bot_settings, threshold):
    import time
    from backend.core.logger import logger
    from backend.services.market import get_asset_current_price
    from backend.sentix_adapter import sentix_state, _save_sentix_db
    
    live_price = get_asset_current_price(target_asset)
    if not live_price or live_price <= 0.0:
        print(f"[Refactored Engine] Failed to resolve current live price for asset {target_asset}. Aborting trade.")
        return
        
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
    
    risk = _calculate_risk_parameters(bot_settings, live_price, decision, strategy)
    
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
                    "closeReason": None, "pnl": 0.0, "headline": headline, "type": "SIMULATED"
                }
                if strategy == "HEDGING":
                    sim["strategyReasoning"] = f"[HEDGING Strategy] Dual directional entry. {trade_decision.get('strategyReasoning', '')}"
                db["savedTrades"].insert(0, sim)
                db["savedTrades"] = db["savedTrades"][:100]

            if strategy == "HEDGING":
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "LONG" for t in existing_trades): add_db_trade("LONG", risk["long_sl"], risk["long_tp"])
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset and t.get("decision") == "SHORT" for t in existing_trades): add_db_trade("SHORT", risk["short_sl"], risk["short_tp"])
            else:
                if not any(t.get("status") == "OPEN" and t.get("targetAsset") == target_asset for t in existing_trades):
                    add_db_trade(decision, risk["sl_price"], risk["tp_price"])
            await write_database_async(db)
            
        from backend.services.telegram_client import send_telegram_alert
        import asyncio
        asyncio.create_task(send_telegram_alert(f"🚀 *Simulated Trade Opened* 🚀\n\n*Asset*: {target_asset}\n*Action*: {decision}\n*Entry Price*: ${live_price}\n*Confidence*: {confidence}%\n*SL*: {risk['sl_pct_raw']}% | *TP*: {risk['tp_pct_raw']}%\n*Reason*: {trade_decision.get('strategyReasoning', '')}"))

# Trigger simulated trade in paper trading mode
async def trigger_automated_trade_sim(item: Dict[str, Any], config: Dict[str, Any]):
    from backend.core.logger import logger
    from backend.services.news import analyze_sentiment
    import time
    
    try:
        headline = item["title"]
        source = item.get("source", "Unknown")
        
        if not is_headline_relevant(headline, source):
            logger.info(f"[Sim Trading] Skipping LLM for irrelevant headline: {headline}")
            sentiment_res = analyze_sentiment(headline)
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
        
        target_asset, decision, confidence, strategy, trade_decision, veto_active, correlation_log = await _evaluate_llm_trade_signal(headline, item, config, bot_settings)
        threshold = bot_settings.get("minConfidence", config.get("confidenceThreshold", 75))
        
        await _execute_simulated_trade(headline, target_asset, decision, confidence, strategy, trade_decision, correlation_log, veto_active, bot_settings, threshold)
        
    except Exception as err:
        logger.error(f"[Sim Trading] Error running automated trade: {err}")
