"""AI Bot evaluation and automation loop extracted from main.py."""
import time
import asyncio
from backend.core.logger import logger
from backend.services.news import news_feed
from backend.helpers.utils import get_asset_current_price


async def _evaluate_llm_trade_signal(headline, item, config, bot_settings):
    from backend.services.market import assets, calculate_asset_beta
    from backend.models.schemas import AIAnalyzeRequest
    
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
    
    # Import analyze_ai from routes
    from backend.routes.ai import analyze_ai
    analysis_res = await analyze_ai(req)
    analysis = analysis_res.get("analysis", {})
    trade_decision = analysis.get("tradeDecision", {})
    veto_gate = analysis.get("vetoGate", {})
    
    trade_decision["targetAsset"] = active_asset
    decision = trade_decision.get("decision", "HOLD")
    confidence = trade_decision.get("confidence", 0)
    
    # Perbaikan untuk LLM Lokal yang gagal memberikan reasoning pada fallback sideways
    if not trade_decision.get("strategyReasoning"):
        if "sideways" in headline.lower():
            trade_decision["strategyReasoning"] = "Pasar kripto sedang sideways tanpa katalis berita signifikan. Bot menggunakan indikator murni."
        else:
            trade_decision["strategyReasoning"] = "LLM tidak menyertakan alasan spesifik. Mengikuti indikator teknikal."
    
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
    
    # Enforce Veto bypass logic mapping central vetoGateMode setting
    veto_mode = bot_settings.get("vetoGateMode", "AUTO").upper()
    if veto_mode == "ON":
        bypass_veto = False
    elif veto_mode == "OFF":
        bypass_veto = True
    else: # AUTO
        bypass_veto = strategy in ["AGGRESSIVE", "SCALPING", "HEDGING"]
        
    veto_active = False if bypass_veto else veto_gate.get("vetoActive", False)
    
    return active_asset, decision, confidence, strategy, trade_decision, veto_active, correlation_log


async def ai_bot_automated_loop():
    """Background task to run AI bot automation strategy periodically when enabled."""
    logger.info("[AI Bot Loop] Starting automated strategy evaluation loop...")
    from backend.sentix_adapter import sentix_state
    from backend.database import load_ai_config
    from backend.trading.simulator import trigger_automated_trade_sim
    from backend.trading.monitor import force_close_all_simulated_positions
    
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
            
            settings_changed = (symbol != last_symbol) or (strategy != last_strategy)
            if (enabled and not last_enabled) or (enabled and settings_changed):
                logger.info(f"[AI Bot Loop] Activation toggle or settings changed (Symbol: {symbol}, Strategy: {strategy}). Resetting throttle and evaluating immediately.")
                last_run_time = 0
                last_evaluated_key = None
            elif not enabled and last_enabled:
                logger.info("[AI Bot Loop] Bot disabled. Force closing all active positions...")
                await force_close_all_simulated_positions()
                last_run_time = 0
                last_evaluated_key = None
                
            last_enabled = enabled
            last_symbol = symbol
            last_strategy = strategy
            
            if enabled:
                now = time.time()
                interval = bot_settings.get("runIntervalSeconds", 60)
                
                if now - last_run_time >= interval:
                    headline = "Pasar Cryptocurrency menunjukkan pergerakan sideways yang stabil."
                    source = "System Indicator"
                    
                    if news_feed:
                        latest_headline = news_feed[0].get("headline", headline)
                        from backend.helpers.utils import is_headline_processed
                        # Jika berita terakhir belum diproses, gunakan berita tersebut.
                        # Jika sudah, kita fallback ke "sideways" agar bot tetap melakukan periodic check.
                        if not is_headline_processed(latest_headline):
                            headline = latest_headline
                            source = news_feed[0].get("source", "System Indicator")
                    
                    current_key = f"{headline}-{symbol}-{strategy}"
                    # Skip jika berita asli (bukan sideways) sudah dievaluasi sebelumnya (mencegah spam)
                    if current_key == last_evaluated_key and "sideways" not in headline.lower():
                        await asyncio.sleep(1)
                        continue
                    
                    last_run_time = now
                    last_evaluated_key = current_key
                    
                    config = await load_ai_config() or {}
                    
                    multi_asset = bot_settings.get("multiAssetMode", False)
                    if multi_asset:
                        # Scan all available symbols in multi-asset mode
                        supported_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SUIUSDT", "DOGEUSDT"]
                        logger.info(f"[AI Bot Loop] Multi-asset mode active. Scanning symbols: {supported_symbols}")
                        
                        for sym in supported_symbols:
                            # Create a localized temporary copy of settings for this specific symbol evaluation
                            temp_settings = dict(bot_settings)
                            temp_settings["symbol"] = sym
                            
                            # Run evaluation for this symbol in pipeline
                            dummy_item = {"title": headline, "source": source}
                            # Construct local key prefix for each symbol to log correctly
                            logger.info(f"[AI Bot Loop] Triggering cycle for {sym}")
                            
                            # Adapt trigger_automated_trade_sim to support passing dynamic target symbol override
                            # Let's import the local strategy evaluator directly
                            try:
                                target_asset, decision, confidence, strategy_val, trade_decision, veto_active, correlation_log = await _evaluate_llm_trade_signal(
                                    headline, dummy_item, config, temp_settings
                                )
                                threshold = temp_settings.get("minConfidence", config.get("confidenceThreshold", 75))
                                
                                # Enforce Veto override bypass for multi-asset mapping settings
                                veto_mode = temp_settings.get("vetoGateMode", "AUTO").upper()
                                if veto_mode == "ON":
                                    veto_active = veto_active or False
                                elif veto_mode == "OFF":
                                    veto_active = False
                                
                                # Enforce BTC SHIELD Correlation Logic for Altcoins
                                if target_asset != "BTC" and decision in ["LONG", "SHORT"]:
                                    # Check override bypass first
                                    if veto_mode == "OFF":
                                        logger.info(f"[BTC SHIELD] Force Off active. Bypassing correlation filter for {target_asset}.")
                                        correlation_log += f" | BTC SHIELD BYPASSED (FORCE OFF)"
                                    else:
                                        # Fetch current BTC matrix status
                                        from backend.services.market import assets, calculate_asset_beta
                                        hist_target = []
                                        hist_btc = []
                                        for a in assets:
                                            if a["symbol"].upper() == target_asset:
                                                hist_target = a["history"]
                                            elif a["symbol"].upper() == "BTC":
                                                hist_btc = a["history"]
                                                
                                        if hist_target and hist_btc:
                                            stats = calculate_asset_beta(hist_target, hist_btc)
                                            r_val = stats["correlation"]
                                            
                                            # Let's inspect BTC's current trend from recent prices
                                            btc_price_trend = "UP" if hist_btc[-1] >= hist_btc[-2] else "DOWN"
                                            
                                            # Filter 1: ALT DIVERGENCE (HEDGE) -> Alt is moving opposite to BTC when BTC goes down
                                            # (Correlation < 0, and we want to SHORT/LONG differently)
                                            # Filter 2: ALT MOMENTUM (FOLLOW) -> Alt is highly correlated (> 0.7) and riding the BTC wave
                                            shield_passed = False
                                            shield_reason = ""
                                            
                                            if btc_price_trend == "DOWN" and r_val < 0.0:
                                                shield_passed = True
                                                shield_reason = f"BTC Shield: Divergence detected (r={r_val}). Alt is decoupling during BTC drop."
                                            elif btc_price_trend == "UP" and r_val > 0.70:
                                                shield_passed = True
                                                shield_reason = f"BTC Shield: Strong correlation detected (r={r_val}). Alt is following BTC momentum."
                                            elif target_asset in ["ETH", "SOL"] and abs(r_val) >= 0.50:
                                                # High cap exception: Allow moderate correlation
                                                shield_passed = True
                                                shield_reason = f"BTC Shield: High-cap correlation match (r={r_val})."
                                                
                                            if not shield_passed:
                                                logger.info(f"[BTC SHIELD] VETO trade on {target_asset}. Correlation {r_val} does not satisfy Shield filters.")
                                                # Veto the trade
                                                veto_active = True
                                                correlation_log += f" | BTC SHIELD VETO (r={r_val}, BTC={btc_price_trend})"
                                            else:
                                                logger.info(f"[BTC SHIELD] PASS trade on {target_asset}. Reason: {shield_reason}")
                                                correlation_log += f" | {shield_reason}"
                                            
                                from backend.trading.simulator import _execute_simulated_trade
                                await _execute_simulated_trade(
                                    headline, target_asset, decision, confidence, strategy_val, 
                                    trade_decision, correlation_log, veto_active, temp_settings, threshold
                                )
                            except Exception as eval_err:
                                logger.error(f"[AI Bot Loop] Evaluation failed for {sym}: {eval_err}")
                    else:
                        dummy_item = {"title": headline, "source": source}
                        logger.info(f"[AI Bot Loop] Strategy automation triggered for headline: {headline}")
                        await trigger_automated_trade_sim(dummy_item, config)
                    
        except Exception as e:
            logger.error(f"[AI Bot Loop] Error: {e}")
            
        await asyncio.sleep(5)
