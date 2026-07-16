import asyncio
import time
from typing import List, Dict, Any, Optional

class LiveSimulationManager:
    def __init__(self):
        self.active = False
        self.strategy = "CONSERVATIVE"
        self.initial_capital = 5000.0
        self.current_capital = 5000.0
        self.target_assets = ["BTC", "ETH", "SOL", "BNB"]
        self.start_time = 0.0
        self.trades = []
        self.logs = []
        self.monitor_task = None
        self.confidence_threshold = 75
        self.bollinger_std_dev = 2.0

    def add_log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.insert(0, f"[{timestamp}] {message}")
        self.logs = self.logs[:100]
        print(f"[Live Sim Manager] {message}")

    async def start_session(self, strategy: str, initial_capital: float, target_assets: List[str], confidence_threshold: int = 75, bollinger_std_dev: float = 2.0):
        if self.active:
            self.add_log("Session already active. Stopping existing session first...")
            await self.stop_session()

        self.strategy = strategy
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.target_assets = [a.upper() for a in target_assets]
        self.confidence_threshold = confidence_threshold
        self.bollinger_std_dev = bollinger_std_dev
        self.start_time = time.time()
        self.trades = []
        self.logs = []
        self.active = True
        
        self.add_log(f"STARTED SESSION - Strategy: {strategy} | Capital: ${initial_capital} | Assets: {', '.join(target_assets)} | AI Veto Threshold: {confidence_threshold}% | BB Dev: {bollinger_std_dev}")
        
        # Start background monitor loop
        self.monitor_task = asyncio.create_task(self.monitor_loop())

    async def stop_session(self):
        if not self.active:
            return
        
        self.active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            self.monitor_task = None
            
        # Close any open positions immediately
        for trade in self.trades:
            if trade.get("status") == "OPEN":
                trade["status"] = "CLOSED"
                trade["closeReason"] = "SESSION_TERMINATED"
                trade["exitPrice"] = trade.get("currentPrice")
                trade["closeTime"] = int(time.time() * 1000)
                self.add_log(f"Closed active position on {trade['targetAsset']} due to session termination.")
                
        self.add_log(f"STOPPED SESSION - Final Capital: ${self.current_capital:.2f} | Net PnL: ${self.current_capital - self.initial_capital:.2f}")

    # Helper to get real-time price from Binance or simulation
    def get_asset_price(self, symbol: str) -> float:
        from backend.services.market import assets
        clean_sym = symbol.upper().replace("USDT", "")
        for a in assets:
            if a["symbol"].upper() == clean_sym:
                return a["price"]
        return 0.0

    async def handle_new_news(self, item: Dict[str, Any]):
        if not self.active:
            return
        
        headline = item["title"]
        self.add_log(f"New headline scraped: '{headline[:50]}...' Processing strategy...")

        # 1. CONSERVATIVE STRATEGY (AI + ML Veto + OOD)
        if self.strategy == "CONSERVATIVE":
            from backend.main import AIAnalyzeRequest, analyze_ai
            from backend.database import load_ai_config
            
            config = await load_ai_config() or {}
            req = AIAnalyzeRequest(
                headline=headline,
                source=item.get("source", "Scraper"),
                provider=config.get("provider", "gemini"),
                customUrl=config.get("customUrl", ""),
                customKey=config.get("customKey", ""),
                customModel=config.get("customModel", "")
            )
            try:
                res = await analyze_ai(req)
                analysis = res.get("analysis", {})
                trade_decision = analysis.get("tradeDecision", {})
                veto_gate = analysis.get("vetoGate", {})
                
                decision = trade_decision.get("decision", "HOLD")
                target_asset = trade_decision.get("targetAsset", "BTC").upper().replace("USDT", "")
                
                # Check target asset whitelist
                if target_asset not in self.target_assets:
                    self.add_log(f"AI recommended {target_asset} which is not in whitelist. Ignored.")
                    return
                    
                if decision in ["LONG", "SHORT"] and not veto_gate.get("vetoActive", False):
                    confidence = trade_decision.get("confidence", 0)
                    threshold = config.get("confidenceThreshold", 75)
                    if confidence >= threshold:
                        # Extract dynamic SL/TP from AI recommendation
                        sl_str = trade_decision.get("recommendedStopLoss", "2.0%").replace("%", "")
                        try:
                            sl_pct = float(sl_str)
                        except ValueError:
                            sl_pct = 2.0
                        tp_pct = sl_pct * 2.0
                        
                        await self.open_simulated_position(
                            decision, target_asset, confidence, 
                            trade_decision.get("strategyReasoning", ""), headline,
                            sl_pct=sl_pct, tp_pct=tp_pct
                        )
                    else:
                        self.add_log(f"AI decision {decision} confidence {confidence}% below threshold {threshold}%. Ignored.")
                else:
                    self.add_log(f"AI decision: {decision} | Veto Gate Active: {veto_gate.get('vetoActive', False)}")
            except Exception as e:
                self.add_log(f"Conservative strategy analysis error: {e}")

        # 2. AGGRESSIVE STRATEGY (AI only, bypass ML Veto & OOD)
        elif self.strategy == "AGGRESSIVE":
            from backend.main import AIAnalyzeRequest, analyze_ai
            from backend.database import load_ai_config
            
            config = await load_ai_config() or {}
            req = AIAnalyzeRequest(
                headline=headline,
                source=item.get("source", "Scraper"),
                provider=config.get("provider", "gemini"),
                customUrl=config.get("customUrl", ""),
                customKey=config.get("customKey", ""),
                customModel=config.get("customModel", "")
            )
            try:
                res = await analyze_ai(req)
                analysis = res.get("analysis", {})
                trade_decision = analysis.get("tradeDecision", {})
                
                decision = trade_decision.get("decision", "HOLD")
                target_asset = trade_decision.get("targetAsset", "BTC").upper().replace("USDT", "")
                
                if target_asset not in self.target_assets:
                    self.add_log(f"AI recommended {target_asset} which is not in whitelist. Ignored.")
                    return
                    
                if decision in ["LONG", "SHORT"]:
                    confidence = trade_decision.get("confidence", 0)
                    # Extract dynamic SL/TP from AI recommendation
                    sl_str = trade_decision.get("recommendedStopLoss", "2.0%").replace("%", "")
                    try:
                        sl_pct = float(sl_str)
                    except ValueError:
                        sl_pct = 2.0
                    tp_pct = sl_pct * 2.0
                    
                    await self.open_simulated_position(
                        decision, target_asset, confidence, 
                        trade_decision.get("strategyReasoning", ""), headline,
                        sl_pct=sl_pct, tp_pct=tp_pct
                    )
                else:
                    self.add_log(f"AI decision: {decision} (Aggressive)")
            except Exception as e:
                self.add_log(f"Aggressive strategy analysis error: {e}")

        # 3. MOMENTUM STRATEGY (Technical Volatility Breakout)
        elif self.strategy == "MOMENTUM":
            self.add_log("Momentum strategy active. Headline ignored (purely technical-driven).")

        # 4. HYBRID STRATEGY (Momentum + AI & ML Veto)
        elif self.strategy == "MOMENTUM_CONSERVATIVE":
            self.add_log("Hybrid Momentum-Conservative strategy active. Checking news sentiment...")
            from backend.main import AIAnalyzeRequest, analyze_ai
            from backend.database import load_ai_config
            
            config = await load_ai_config() or {}
            req = AIAnalyzeRequest(
                headline=headline,
                source=item.get("source", "Scraper"),
                provider=config.get("provider", "gemini"),
                customUrl=config.get("customUrl", ""),
                customKey=config.get("customKey", ""),
                customModel=config.get("customModel", "")
            )
            try:
                res = await analyze_ai(req)
                analysis = res.get("analysis", {})
                trade_decision = analysis.get("tradeDecision", {})
                veto_gate = analysis.get("vetoGate", {})
                
                decision = trade_decision.get("decision", "HOLD")
                target_asset = trade_decision.get("targetAsset", "BTC").upper().replace("USDT", "")
                
                # Check target asset whitelist
                if target_asset not in self.target_assets:
                    self.add_log(f"Hybrid recommended {target_asset} which is not in whitelist. Ignored.")
                    return
                    
                if decision in ["LONG", "SHORT"] and not veto_gate.get("vetoActive", False):
                    confidence = trade_decision.get("confidence", 0)
                    threshold = config.get("confidenceThreshold", 75)
                    if confidence >= threshold:
                        # Fundamental signal approved. Now check Technical confirmation (Momentum)
                        # For LONG, we want the current price to be above the 20-period SMA
                        # For SHORT, we want the current price to be below the 20-period SMA
                        from backend.services.market import assets
                        confirmed = False
                        reason = ""
                        for a in assets:
                            if a["symbol"].upper() == target_asset:
                                history = a.get("history", [])
                                if len(history) >= 20:
                                    prices_20 = history[-20:]
                                    sma = sum(prices_20) / 20.0
                                    cur_price = a["price"]
                                    if decision == "LONG" and cur_price > sma:
                                        confirmed = True
                                        reason = f"Technical confirmation: Price (${cur_price:.2f}) is above SMA-20 (${sma:.2f})"
                                    elif decision == "SHORT" and cur_price < sma:
                                        confirmed = True
                                        reason = f"Technical confirmation: Price (${cur_price:.2f}) is below SMA-20 (${sma:.2f})"
                                    else:
                                        reason = f"Technical rejection: Price (${cur_price:.2f}) does not support {decision} relative to SMA-20 (${sma:.2f})"
                                else:
                                    reason = "Technical rejection: Insufficient price history (less than 20 ticks)"
                                break
                        
                        if confirmed:
                            # Extract dynamic SL/TP from AI recommendation
                            sl_str = trade_decision.get("recommendedStopLoss", "2.0%").replace("%", "")
                            try:
                                sl_pct = float(sl_str)
                            except ValueError:
                                sl_pct = 2.0
                            tp_pct = sl_pct * 2.0
                            
                            await self.open_simulated_position(
                                decision, target_asset, confidence, 
                                f"{trade_decision.get('strategyReasoning', '')} | {reason}", headline,
                                sl_pct=sl_pct, tp_pct=tp_pct
                            )
                        else:
                            self.add_log(f"Hybrid trade rejected. {reason}")
                    else:
                        self.add_log(f"AI decision {decision} confidence {confidence}% below threshold {threshold}%. Ignored.")
                else:
                    self.add_log(f"AI decision: {decision} | Veto Gate Active: {veto_gate.get('vetoActive', False)}")
            except Exception as e:
                self.add_log(f"Hybrid strategy analysis error: {e}")

    async def check_momentum_strategy(self):
        from backend.services.market import assets
        for a in assets:
            symbol = a["symbol"].upper()
            if symbol not in self.target_assets:
                continue
                
            if any(t["status"] == "OPEN" and t["targetAsset"] == symbol for t in self.trades):
                continue
                
            history = a.get("history", [])
            if len(history) < 20:
                continue
                
            prices_20 = history[-20:]
            sma = sum(prices_20) / 20.0
            variance = sum((p - sma) ** 2 for p in prices_20) / 20.0
            stddev = variance ** 0.5
            if stddev <= 0.0001:
                continue
                
            std_dev_mult = getattr(self, "bollinger_std_dev", 2.0)
            upper_bb = sma + (std_dev_mult * stddev)
            lower_bb = sma - (std_dev_mult * stddev)
            cur_price = a["price"]
            
            if cur_price > upper_bb:
                await self.open_simulated_position("LONG", symbol, 80, f"Technical breakout above Upper Bollinger Band (${upper_bb:.2f})", "Technical Bollinger Bands Breakout")
            elif cur_price < lower_bb:
                await self.open_simulated_position("SHORT", symbol, 80, f"Technical breakout below Lower Bollinger Band (${lower_bb:.2f})", "Technical Bollinger Bands Breakout")

    async def check_momentum_conservative_strategy(self):
        from backend.services.market import assets
        from backend.services.news import news_feed
        from backend.main import AIAnalyzeRequest, analyze_ai
        from backend.database import load_ai_config
        
        if not news_feed:
            return

        latest_news = news_feed[0]
        headline = latest_news.get("headline") or latest_news.get("title") or "Market trades normally."

        for a in assets:
            symbol = a["symbol"].upper()
            if symbol not in self.target_assets:
                continue
                
            if any(t["status"] == "OPEN" and t["targetAsset"] == symbol for t in self.trades):
                continue
                
            history = a.get("history", [])
            if len(history) < 20:
                continue
                
            prices_20 = history[-20:]
            sma = sum(prices_20) / 20.0
            variance = sum((p - sma) ** 2 for p in prices_20) / 20.0
            stddev = variance ** 0.5
            if stddev <= 0.0001:
                continue
                
            std_dev_mult = getattr(self, "bollinger_std_dev", 2.0)
            upper_bb = sma + (std_dev_mult * stddev)
            lower_bb = sma - (std_dev_mult * stddev)
            cur_price = a["price"]
            
            tech_decision = None
            reasoning = ""
            if cur_price > upper_bb:
                tech_decision = "LONG"
                reasoning = f"Technical breakout above Upper Bollinger Band (${upper_bb:.2f})"
            elif cur_price < lower_bb:
                tech_decision = "SHORT"
                reasoning = f"Technical breakout below Lower Bollinger Band (${lower_bb:.2f})"
                
            if tech_decision:
                self.add_log(f"Technical {tech_decision} breakout detected on {symbol}. Running AI + ML Veto validation on latest news...")
                
                config = await load_ai_config() or {}
                req = AIAnalyzeRequest(
                    headline=headline,
                    source=latest_news.get("source", "Scraper"),
                    provider=config.get("provider", "gemini"),
                    customUrl=config.get("customUrl", ""),
                    customKey=config.get("customKey", ""),
                    customModel=config.get("customModel", "")
                )
                try:
                    res = await analyze_ai(req)
                    analysis = res.get("analysis", {})
                    trade_decision = analysis.get("tradeDecision", {})
                    veto_gate = analysis.get("vetoGate", {})
                    
                    ai_decision = trade_decision.get("decision", "HOLD")
                    if ai_decision == tech_decision and not veto_gate.get("vetoActive", False):
                        confidence = trade_decision.get("confidence", 0)
                        threshold = getattr(self, "confidence_threshold", config.get("confidenceThreshold", 75))
                        if confidence >= threshold:
                            sl_str = trade_decision.get("recommendedStopLoss", "2.0%").replace("%", "")
                            try:
                                sl_pct = float(sl_str)
                            except ValueError:
                                sl_pct = 2.0
                            tp_pct = sl_pct * 2.0
                            
                            await self.open_simulated_position(
                                tech_decision, symbol, confidence, 
                                f"{reasoning} | Confirmed by AI/ML: {trade_decision.get('strategyReasoning', '')}", 
                                headline, sl_pct=sl_pct, tp_pct=tp_pct
                            )
                        else:
                            self.add_log(f"Hybrid trade rejected: AI confidence {confidence}% below threshold {threshold}%")
                    else:
                        self.add_log(f"Hybrid trade rejected: AI decision '{ai_decision}' does not align with Technical '{tech_decision}', or Veto Gate is active.")
                except Exception as e:
                    self.add_log(f"Hybrid technical validation error: {e}")

    async def open_simulated_position(self, decision: str, target_asset: str, confidence: float, reasoning: str, headline: str, sl_pct: float = 2.0, tp_pct: float = 4.0):
        # Prevent duplicate open positions on same asset to keep risk managed
        if any(t["status"] == "OPEN" and t["targetAsset"] == target_asset for t in self.trades):
            self.add_log(f"Already have an open position on {target_asset}. Skipping.")
            return

        cur_price = self.get_asset_price(target_asset)
        if cur_price <= 0.0:
            self.add_log(f"Could not resolve current price for asset {target_asset}.")
            return

        # Allocate 10% of current capital as margin
        margin = self.current_capital * 0.1
        if margin <= 10.0:
            self.add_log("Margin amount is too low. Cannot open simulated trade.")
            return

        # Leverage: fixed 5x for simplicity
        leverage = 5.0

        trade = {
            "id": f"sim-{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "decision": decision,
            "targetAsset": target_asset,
            "confidence": confidence,
            "recommendedLeverage": f"{int(leverage)}x",
            "recommendedStopLoss": f"{sl_pct}%",
            "recommendedTakeProfit": f"{tp_pct}%",
            "strategyReasoning": reasoning,
            "status": "OPEN",
            "entryPrice": cur_price,
            "currentPrice": cur_price,
            "exitPrice": None,
            "closeTime": None,
            "closeReason": None,
            "marginAllocated": margin,
            "pnl": 0.0,
            "headline": headline
        }

        self.trades.insert(0, trade)
        self.add_log(f"Opened simulated position: {decision} {target_asset} at {cur_price} | Margin: ${margin:.2f} | SL: {sl_pct}% | TP: {tp_pct}%")

        # Telegram notification if possible
        try:
            from backend.services.telegram_client import send_telegram_alert
            msg = (
                f"📊 *[Session Trade]* Simulated {decision} {target_asset} Opened!\n"
                f"Entry Price: ${cur_price}\n"
                f"Margin: ${margin:.2f}\n"
                f"Strategy: {self.strategy}\n"
                f"Reason: {reasoning[:80]}..."
            )
            asyncio.create_task(send_telegram_alert(msg))
        except Exception:
            pass

    async def monitor_loop(self):
        self.add_log("Started real-time position monitor loop.")
        while self.active:
            try:
                if self.strategy == "MOMENTUM":
                    await self.check_momentum_strategy()
                elif self.strategy == "MOMENTUM_CONSERVATIVE":
                    await self.check_momentum_conservative_strategy()
                
                updated = False
                for trade in self.trades:
                    if trade.get("status") == "OPEN":
                        symbol = trade.get("targetAsset", "")
                        cur_price = self.get_asset_price(symbol)
                        if cur_price <= 0:
                            continue

                        trade["currentPrice"] = cur_price
                        entry_price = trade.get("entryPrice", cur_price)
                        margin = trade.get("marginAllocated", 0.0)
                        
                        leverage = 5.0
                        
                        # Extract SL/TP from trade object
                        sl_str = trade.get("recommendedStopLoss", "2.0%").replace("%", "")
                        try:
                            sl_pct = float(sl_str)
                        except ValueError:
                            sl_pct = 2.0
                            
                        tp_str = trade.get("recommendedTakeProfit", "4.0%").replace("%", "")
                        try:
                            tp_pct = float(tp_str)
                        except ValueError:
                            tp_pct = 4.0
                            
                        decision = trade.get("decision")

                        if decision == "LONG":
                            price_change_pct = ((cur_price - entry_price) / entry_price) * 100
                        else:
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
                            
                            pnl_usd = margin * (pnl_pct / 100.0)
                            self.current_capital += pnl_usd
                            
                            self.add_log(f"Closed simulated position: {decision} {symbol} on {close_reason} | PnL: {pnl_pct:.2f}% (${pnl_usd:.2f})")
                            
                            try:
                                from backend.services.telegram_client import send_telegram_alert
                                closed_msg = (
                                    f"🏁 *[Session Trade]* Simulated {decision} {symbol} Closed ({close_reason})!\n"
                                    f"Exit Price: ${cur_price}\n"
                                    f"PnL: {pnl_pct:.2f}% (${pnl_usd:.2f})\n"
                                    f"Current Wallet Balance: ${self.current_capital:.2f}"
                                )
                                asyncio.create_task(send_telegram_alert(closed_msg))
                            except Exception:
                                pass
                            
                            updated = True
                
            except Exception as e:
                self.add_log(f"Monitor loop error: {e}")
            await asyncio.sleep(5) # Check every 5 seconds

# Singleton Instance
live_sim_manager = LiveSimulationManager()
