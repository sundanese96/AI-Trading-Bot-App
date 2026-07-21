"""Position monitoring loops extracted from main.py."""
import time
import asyncio
from backend.core.logger import logger
from backend.helpers.utils import get_asset_current_price
from backend.sentix_adapter import sentix_state


async def monitor_simulated_positions_loop():
    """Monitor and auto-close simulated positions based on SL/TP/Timeout."""
    logger.info("[Sim Position Monitor] Starting simulated position monitor loop...")
    while True:
        try:
            from backend.database import db_lock, read_database_async, write_database_async
            
            async with db_lock:
                db = await read_database_async()
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
                        
                        tp_str = str(trade.get("recommendedTakeProfit", f"{sl_pct * 2.0}%")).replace("%", "")
                        try:
                            tp_pct = float(tp_str)
                        except ValueError:
                            tp_pct = sl_pct * 2.0
                        decision = trade.get("decision")
                        
                        if decision == "LONG":
                            price_change_pct = ((cur_price - entry_price) / entry_price) * 100
                        else: # SHORT
                            price_change_pct = ((entry_price - cur_price) / entry_price) * 100
                            
                        pnl_pct = price_change_pct * leverage
                        margin_used = trade.get("margin", entry_price)
                        pnl_dollar = (pnl_pct / 100.0) * margin_used
                        trade["pnl"] = round(pnl_dollar, 2)
                        
                        triggered_close = False
                        close_reason = ""
                        
                        ts_pct = float(sentix_state.get("aiBotSettings", {}).get("trailingStopPct", 0.5))
                        
                        if decision == "LONG":
                            trade["highestPrice"] = max(trade.get("highestPrice", cur_price), cur_price)
                            if ts_pct > 0 and cur_price <= trade["highestPrice"] * (1 - ts_pct / 100):
                                triggered_close = True
                                close_reason = "TRAILING_STOP"
                        else:
                            trade["lowestPrice"] = min(trade.get("lowestPrice", cur_price), cur_price) if trade.get("lowestPrice") else cur_price
                            if ts_pct > 0 and cur_price >= trade["lowestPrice"] * (1 + ts_pct / 100):
                                triggered_close = True
                                close_reason = "TRAILING_STOP"
                        
                        # 1. Stop Loss check
                        if not triggered_close and price_change_pct <= -sl_pct:
                            triggered_close = True
                            close_reason = "STOP_LOSS"
                        # 2. Take Profit check
                        elif not triggered_close and price_change_pct >= tp_pct:
                            triggered_close = True
                            close_reason = "TAKE_PROFIT"
                        # 3. Timeout check (Configurable)
                        elif not triggered_close:
                            max_hold_mins = int(sentix_state.get("aiBotSettings", {}).get("maxHoldMinutes", 0))
                            if max_hold_mins > 0 and int(time.time() * 1000) - trade.get("timestamp", 0) >= max_hold_mins * 60 * 1000:
                                triggered_close = True
                                close_reason = "TIMEOUT"
                            
                        if triggered_close:
                            trade["status"] = "CLOSED"
                            trade["exitPrice"] = cur_price
                            trade["closeTime"] = int(time.time() * 1000)
                            trade["closeReason"] = close_reason
                            
                            # Also close matching trade in Sentix db.json
                            try:
                                from backend.sentix_adapter import close_active_position_by_timestamp
                                await close_active_position_by_timestamp(trade.get("timestamp"), cur_price, close_reason)
                            except Exception as sentix_err:
                                logger.error(f"[Sim Position Monitor] Error closing Sentix trade: {sentix_err}")
                            
                            # Append to pnlLog for rolling daily stats
                            if "pnlLog" not in db:
                                db["pnlLog"] = []
                            db["pnlLog"].append({
                                "timestamp": int(time.time() * 1000),
                                "pnl": round(pnl_dollar, 2)
                            })
                            
                            # Send Telegram notification for the closed simulated position!
                            from backend.services.telegram_client import send_telegram_alert
                            closed_msg = (
                                f"🏁 *Simulated Trade Closed ({close_reason})* 🏁\n\n"
                                f"*Asset*: {symbol}\n"
                                f"*Action*: {decision}\n"
                                f"*Entry Price*: ${entry_price}\n"
                                f"*Exit Price*: ${cur_price}\n"
                                f"*Final PnL*: ${round(pnl_dollar, 2)} ({'🟢 Profit' if pnl_dollar > 0 else '🔴 Loss'})\n"
                                f"*Headline*: {trade.get('headline', '')}"
                            )
                            asyncio.create_task(send_telegram_alert(closed_msg))
                            logger.info(f"[Sim Position Monitor] CLOSED POSITION: {decision} {symbol} at {cur_price} | PnL: ${pnl_dollar:.2f}")
                            
                        updated = True
                        
                if updated:
                    await write_database_async(db)
                    
        except Exception as loop_err:
            logger.error(f"[Sim Position Monitor] Error in loop: {loop_err}")
        await asyncio.sleep(10) # check every 10 seconds


async def force_close_all_simulated_positions():
    """Force close all open simulated positions when bot is disabled."""
    from backend.sentix_adapter import sentix_state, _save_sentix_db
    from backend.database import db_lock, read_database_async, write_database_async
    
    closed_count = 0
    # 1. Close all sentix_state trades
    if "trades" in sentix_state:
        for trade in sentix_state["trades"]:
            if trade.get("status") == "OPEN":
                symbol = trade.get("symbol", "").replace("USDT", "")
                cur_price = get_asset_current_price(symbol)
                if cur_price <= 0:
                    cur_price = trade.get("entryPrice", 0)
                
                trade["status"] = "CLOSED"
                trade["exitPrice"] = cur_price
                trade["exitTimestamp"] = int(time.time() * 1000)
                trade["reason"] = "BOT_DISABLED"
                
                entry_price = trade.get("entryPrice", cur_price)
                price_diff = (cur_price - entry_price) if trade.get("type") == "BUY" else (entry_price - cur_price)
                raw_return = price_diff / entry_price if entry_price > 0 else 0
                size = trade.get("size", 0)
                leverage = trade.get("leverage", 1)
                
                fee = size * entry_price * 0.001
                gross_pnl = raw_return * (size * entry_price)
                net_pnl = gross_pnl - fee
                trade["pnl"] = round(net_pnl, 2)
                
                margin_used = (size * entry_price) / leverage if leverage > 0 else 0
                refund = margin_used + net_pnl
                sentix_state["portfolio"]["balanceUSD"] = round(sentix_state["portfolio"].get("balanceUSD", 0) + refund, 2)
                closed_count += 1
        _save_sentix_db()
        
    # 2. Close all db.json savedTrades
    updated = False
    async with db_lock:
        db = await read_database_async()
        for sim_trade in db.get("savedTrades", []):
            if sim_trade.get("status") == "OPEN" and sim_trade.get("type") == "SIMULATED":
                symbol = sim_trade.get("targetAsset", "")
                cur_price = get_asset_current_price(symbol)
                if cur_price <= 0:
                    cur_price = sim_trade.get("entryPrice", 0)
                
                sim_trade["status"] = "CLOSED"
                sim_trade["exitPrice"] = cur_price
                sim_trade["closeTime"] = int(time.time() * 1000)
                sim_trade["closeReason"] = "BOT_DISABLED"
                
                entry_price = sim_trade.get("entryPrice", cur_price)
                leverage_str = str(sim_trade.get("recommendedLeverage", "5x")).replace("x", "")
                try:
                    leverage = float(leverage_str)
                except ValueError:
                    leverage = 5.0
                    
                price_change_pct = ((cur_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                if sim_trade.get("decision") != "LONG":
                    price_change_pct = -price_change_pct
                margin_used = sim_trade.get("margin", entry_price)
                sim_trade["pnl"] = round((price_change_pct / 100.0) * margin_used, 2)
                updated = True
                
        if updated:
            await write_database_async(db)
            
    if closed_count > 0 or updated:
        from backend.services.telegram_client import send_telegram_alert
        asyncio.create_task(send_telegram_alert("🛑 *AI Bot Dimatikan* 🛑\nSemua posisi trading simulasi yang aktif telah ditutup secara paksa karena mode Strategy Automation dimatikan."))
        logger.info(f"[AI Bot Loop] Force closed {closed_count} bot positions and matching db records.")
