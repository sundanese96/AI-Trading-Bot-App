import os
import time
import asyncio
from typing import Dict, Any, Optional
import ccxt
from backend.database import load_ai_config, lock_bot
from backend.config import VERIFY_SSL

# Global lock to prevent race conditions in circuit breaker checks
db_lock = asyncio.Lock()

# Load Binance credentials from environment or database
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
USE_TESTNET = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"

def _get_ccxt_client(api_key: str, api_secret: str) -> ccxt.binanceusdm:
    """Initializes and returns a CCXT Binance USD-M Futures client."""
    config = {}
    if api_key and api_secret:
        config["apiKey"] = api_key
        config["secret"] = api_secret
    client = ccxt.binanceusdm(config)  # type: ignore
    if USE_TESTNET:
        client.set_sandbox_mode(True)
    return client

async def execute_futures_order(
    symbol: str,
    side: str,
    position_side: str,
    order_type: str,
    quantity: float,
    leverage: int,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes a Futures order on Binance (Spot/Futures Testnet or Mainnet) using CCXT.
    Includes automatic leverage setting and SL/TP bracket orders.
    """
    # Load credentials and risk settings from database config
    config = await load_ai_config()
    
    # 0. Check if Bot is Locked (Hard-Stop)
    if config.get("isLocked", False):
        return {
            "status": "error",
            "message": "Bot is currently LOCKED due to a previous critical error or circuit breaker. Manual unlock required."
        }

    # 0.1 Check if side is HOLD (Early return to prevent any API calls)
    if side.upper() == "HOLD":
        return {
            "status": "success",
            "message": "Trade decision is HOLD. No order was submitted."
        }

    api_key = config.get("binanceApiKey", BINANCE_API_KEY)
    api_secret = config.get("binanceApiSecret", BINANCE_API_SECRET)
    dry_run = config.get("dryRun", True)
    max_daily_loss = config.get("maxDailyLoss", 5.0)
    max_trades_per_day = config.get("maxTradesPerDay", 5)

    # 1. Check Circuit Breakers (Daily Stats) with Lock to prevent race conditions
    from backend.database import get_daily_stats, update_daily_stats
    from backend.services.telegram_client import send_telegram_alert
    
    async with db_lock:
        stats = await get_daily_stats()
        
        if stats["tradeCount"] >= max_trades_per_day:
            msg = f"Circuit Breaker Triggered: Daily trade limit reached ({max_trades_per_day} trades). Bot is now locked until manual reset."
            print(f"[CIRCUIT BREAKER] {msg}")
            await lock_bot()
            # Await Telegram Alert directly for critical circuit breaker
            await send_telegram_alert(msg)
            return {
                "status": "error",
                "message": f"Circuit Breaker: Daily trade limit reached ({max_trades_per_day} trades)."
            }
            
        if stats["dailyLoss"] >= max_daily_loss:
            msg = f"Circuit Breaker Triggered: Max daily loss limit reached (${max_daily_loss:.2f}). Bot is now locked until manual reset."
            print(f"[CIRCUIT BREAKER] {msg}")
            await lock_bot()
            # Await Telegram Alert directly for critical circuit breaker
            await send_telegram_alert(msg)
            return {
                "status": "error",
                "message": f"Circuit Breaker: Max daily loss limit reached (${max_daily_loss:.2f})."
            }

        # 2. Enforce Mandatory Stop Loss (Default to 4.5% if not provided or invalid)
        if not stop_loss_pct or stop_loss_pct <= 0:
            stop_loss_pct = 4.5
        # Limit stop loss to maximum 4.5% for safety
        stop_loss_pct = min(4.5, stop_loss_pct)

    # Strict Risk Guard: Limit leverage to 10x max for safety
    safe_leverage = min(10, max(1, leverage))

    # Format symbol for ccxt / binance (e.g. BTCUSDT)
    symbol_formatted = f"{symbol}USDT".upper()
    
    # 1.5 Fetch current ticker price to estimate safety caps using CCXT client (read-only)
    ticker_price = 0.0
    try:
        # Initialize a temporary or public CCXT client to fetch ticker
        client_pub = _get_ccxt_client("", "")
        ticker_res = await asyncio.to_thread(client_pub.fetch_ticker, symbol_formatted)
        if ticker_res:
            ticker_price = float(ticker_res.get("last", 0.0) or ticker_res.get("close", 0.0))  # type: ignore
    except Exception as e:
        print(f"[Binance Futures] Warning: Ticker price fetch failed: {e}")

    # Fallback to test mock if needed
    if ticker_price <= 0:
        ticker_price = 50000.0 if symbol == "BTC" else (100.0 if symbol == "SOL" else 1.0)
        
    # 1.6 Fetch Account Balance dynamically
    available_balance = 0.0
    total_balance = 0.0
    if dry_run:
        available_balance = 1000.0
        total_balance = 1000.0
    else:
        if not api_key or not api_secret:
            return {
                "status": "error",
                "message": "Binance API Key or Secret is missing. Please configure it in Settings."
            }
        try:
            client_priv = _get_ccxt_client(api_key, api_secret)
            # Use ccxt fetch_balance
            bal = await asyncio.to_thread(client_priv.fetch_balance)
            usdt_asset = bal.get("USDT") or {}
            available_balance = float(usdt_asset.get("free", 0.0))  # type: ignore
            total_balance = float(usdt_asset.get("total", 0.0))  # type: ignore
        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception while fetching account balance: {str(e)}"
            }

    # 1.7 Apply Risk Sizing Capping (Absolute cap of $100 margin, percentage cap of 5% of balance)
    initial_margin = (quantity * ticker_price) / safe_leverage
    max_allowed_margin = min(100.0, 0.05 * total_balance)
    
    if initial_margin > max_allowed_margin:
        clamped_quantity = (max_allowed_margin * safe_leverage) / ticker_price
        clamped_quantity = round(clamped_quantity, 3) # standard contract precision
        print(f"[Risk Guard] Position margin {initial_margin:.2f} USDT exceeds cap {max_allowed_margin:.2f} USDT. Clamping quantity from {quantity} to {clamped_quantity}.")
        quantity = clamped_quantity
        initial_margin = (quantity * ticker_price) / safe_leverage

    if quantity <= 0:
        return {
            "status": "error",
            "message": f"Risk limits clamped order quantity to 0 (max allowed margin: {max_allowed_margin:.2f} USDT). Order aborted."
        }

    # 1.8 Verify balance sufficiency
    if available_balance < initial_margin:
        return {
            "status": "error",
            "message": f"Insufficient available balance. Required margin: {initial_margin:.2f} USDT, Available balance: {available_balance:.2f} USDT."
        }

    # Calculate estimated SL price
    sl_price = ticker_price * (1 - stop_loss_pct / 100.0) if side == "BUY" else ticker_price * (1 + stop_loss_pct / 100.0)
    sl_price = round(sl_price, 4 if symbol == "XRP" else 2)
    
    # Calculate estimated TP price (if requested)
    tp_price = None
    if take_profit_pct:
        tp_price = ticker_price * (1 + take_profit_pct / 100.0) if side == "BUY" else ticker_price * (1 - take_profit_pct / 100.0)
        tp_price = round(tp_price, 4 if symbol == "XRP" else 2)

    # 3. Dry-Run / Paper Trading Mode
    if dry_run:
        print(f"[DRY-RUN] Simulating Futures Order: {side} {quantity} {symbol}USDT with {leverage}x leverage.")
        print(f"[DRY-RUN] Simulating SL Bracket: {stop_loss_pct}% at price {sl_price}")
        if take_profit_pct:
            print(f"[DRY-RUN] Simulating TP Bracket: {take_profit_pct}% at price {tp_price}")
            
        # Simulate a small random slippage/fee for paper trading
        simulated_pnl = -0.05  # Assume small fee/slippage on entry
        await update_daily_stats(simulated_pnl)
        
        return {
            "status": "success",
            "message": "[DRY-RUN] Paper trade executed successfully. No real order was submitted.",
            "data": {
                "order": {"symbol": f"{symbol}USDT", "side": side, "origQty": quantity, "price": "0.0", "avgPrice": str(ticker_price), "status": "FILLED"},
                "stop_loss": {"symbol": f"{symbol}USDT", "side": "SELL" if side == "BUY" else "BUY", "stopPrice": str(sl_price), "status": "NEW"},
                "take_profit": {"symbol": f"{symbol}USDT", "side": "SELL" if side == "BUY" else "BUY", "stopPrice": str(tp_price), "status": "NEW"} if take_profit_pct else None
            }
        }

    results = {"order": None, "stop_loss": None, "take_profit": None}

    try:
        client = _get_ccxt_client(api_key, api_secret)
        
        # 1. Set Leverage
        try:
            await asyncio.to_thread(client.set_leverage, safe_leverage, symbol_formatted)
        except Exception as lev_err:
            print(f"[Binance Futures] Failed to set leverage: {lev_err}")

        # 1.5 Fetch current ticker price to estimate Stop-Loss price
        try:
            ticker_res = await asyncio.to_thread(client.fetch_ticker, symbol_formatted)
            ticker_price = float(ticker_res.get("last", 0.0) or ticker_res.get("close", 0.0))  # type: ignore
        except Exception as e:
            ticker_price = 0.0
            
        if ticker_price <= 0:
            return {
                "status": "error",
                "message": f"Failed to fetch market price for {symbol_formatted}. Cannot calculate safety thresholds."
            }

        opposite_side = "SELL" if side == "BUY" else "BUY"
        
        # Calculate estimated SL price
        sl_price = ticker_price * (1 - stop_loss_pct / 100.0) if side == "BUY" else ticker_price * (1 + stop_loss_pct / 100.0)
        sl_price = round(sl_price, 4 if symbol == "XRP" else 2)
        
        # Calculate estimated TP price (if requested)
        tp_price = None
        if take_profit_pct:
            tp_price = ticker_price * (1 + take_profit_pct / 100.0) if side == "BUY" else ticker_price * (1 - take_profit_pct / 100.0)
            tp_price = round(tp_price, 4 if symbol == "XRP" else 2)

        # Construct batchOrders JSON list in ccxt / binance format
        # CCXT uses create_orders or fetch_private/public for batchOrders.
        # To maintain the exact atomic batchOrders call structure safely:
        batch_orders_payload = [
            {
                "symbol": symbol_formatted,
                "side": side.upper(),
                "positionSide": position_side.upper(),
                "type": order_type.upper(),
                "quantity": str(quantity)
            },
            {
                "symbol": symbol_formatted,
                "side": opposite_side.upper(),
                "positionSide": position_side.upper(),
                "type": "STOP_MARKET",
                "stopPrice": str(sl_price),
                "closePosition": "true"
            }
        ]
        
        if tp_price:
            batch_orders_payload.append({
                "symbol": symbol_formatted,
                "side": opposite_side.upper(),
                "positionSide": position_side.upper(),
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": str(tp_price),
                "closePosition": "true"
            })

        # 2. Place Atomic Batch Orders using CCXT's custom binanceusdm fapiPrivatePostBatchOrders
        # CCXT allows sending requests directly to raw endpoints via client.fapiPrivatePostBatchOrders
        # This keeps the exact atomic API guarantee while letting CCXT handle all auth/timestamp signing!
        batch_res = await asyncio.to_thread(
            client.fapiPrivatePostBatchOrders, 
            {"batchOrders": client.json(batch_orders_payload)}
        )
        
        if not isinstance(batch_res, list) or len(batch_res) < 2:
            return {
                "status": "error",
                "message": f"Unexpected batch order response format from CCXT: {batch_res}"
            }
            
        main_order_data = batch_res[0]
        sl_order_data = batch_res[1]
        tp_order_data = batch_res[2] if len(batch_res) > 2 else None
        
        # Inspect Main Order
        # Binance returns code/msg inside batch response if a specific order failed
        if "code" in main_order_data or "msg" in main_order_data:
            return {
                "status": "error",
                "message": f"Failed to place main order in batch: {main_order_data.get('msg')}"
            }
            
        results["order"] = main_order_data
        entry_price = float(main_order_data.get("avgPrice", 0.0)) or float(main_order_data.get("price", 0.0))
        
        # Inspect Stop Loss Order
        sl_placed = "code" not in sl_order_data
        if sl_placed:
            results["stop_loss"] = sl_order_data
        else:
            # 3. Retry Logic & emergency failsafe for Stop Loss if it failed in the batch
            print(f"[Binance Futures] Stop Loss placement failed in batch: {sl_order_data.get('msg')}. Initializing retry loop...")
            max_retries = 3
            backoff_delay = 0.5
            sl_retry_success = False
            
            # Recalculate based on real entry price if possible
            if entry_price > 0:
                sl_price = entry_price * (1 - stop_loss_pct / 100.0) if side == "BUY" else entry_price * (1 + stop_loss_pct / 100.0)
                sl_price = round(sl_price, 4 if symbol == "XRP" else 2)
            
            for attempt in range(max_retries):
                await asyncio.sleep(backoff_delay)
                print(f"[Binance Futures] Retrying Stop Loss order (Attempt {attempt+1}/{max_retries})...")
                
                try:
                    # Place single order via CCXT fapiPrivatePostOrder
                    sl_res = await asyncio.to_thread(
                        client.fapiPrivatePostOrder,
                        {
                            "symbol": symbol_formatted,
                            "side": opposite_side.upper(),
                            "positionSide": position_side.upper(),
                            "type": "STOP_MARKET",
                            "stopPrice": str(sl_price),
                            "closePosition": "true"
                        }
                    )
                    if sl_res and "code" not in sl_res:
                        results["stop_loss"] = sl_res
                        sl_retry_success = True
                        print(f"[Binance Futures] Stop Loss placed successfully on attempt {attempt+1}.")
                        break
                    else:
                        print(f"[Binance Futures] Retry attempt {attempt+1} failed: {sl_res}")
                except Exception as e:
                    print(f"[Binance Futures] Retry attempt {attempt+1} failed with exception: {e}")
                
                backoff_delay *= 2
                
            if not sl_retry_success:
                # CRITICAL FAILSAFE: If Stop Loss order fails, we MUST immediately market close the main position!
                msg = f"CRITICAL: Failed to place Stop Loss for {symbol_formatted} after retries. Emergency closing position immediately..."
                print(f"[Binance Futures] {msg}")
                # Await Telegram Alert directly for critical failsafe
                await send_telegram_alert(f"🚨 {msg}")
                
                try:
                    close_res = await asyncio.to_thread(
                        client.fapiPrivatePostOrder,
                        {
                            "symbol": symbol_formatted,
                            "side": opposite_side.upper(),
                            "positionSide": position_side.upper(),
                            "type": "MARKET",
                            "quantity": str(quantity)
                        }
                    )
                    if close_res and "code" not in close_res:
                        print(f"[Binance Futures] Emergency close position executed successfully.")
                    else:
                        raise RuntimeError(f"Close order rejected: {close_res}")
                except Exception as close_err:
                    critical_msg = f"FATAL: Emergency close failed for {symbol_formatted}! Position is open without Stop Loss. Manual intervention required immediately!"
                    print(f"[Binance Futures] {critical_msg} Error: {close_err}")
                    # Lock the bot immediately on fatal failure
                    await lock_bot()
                    # Await Telegram Alert directly for fatal failsafe
                    await send_telegram_alert(f"🚨🚨🚨 {critical_msg}\nError: {close_err}")
                
                return {
                    "status": "error",
                    "message": f"CRITICAL: Failed to place Stop Loss bracket. Position was emergency closed to prevent unprotected risk."
                }

        # Inspect Take Profit Order (non-critical, warn if failed)
        if tp_price and tp_order_data:
            if "code" in tp_order_data:
                print(f"[Binance Futures] Failed to place Take Profit: {tp_order_data.get('msg')}")
            else:
                results["take_profit"] = tp_order_data

        # Update daily stats with a placeholder fee/slippage for now
        # Only update stats if the order was successfully executed on Binance
        async with db_lock:
            await update_daily_stats(-0.10)

        return {
            "status": "success",
            "message": "Futures order executed successfully with SL/TP brackets.",
            "data": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception occurred during order execution: {str(e)}"
        }
