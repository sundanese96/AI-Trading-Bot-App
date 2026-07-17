import asyncio
import time
import httpx
from backend.database import load_ai_config, update_daily_stats, is_trade_processed, mark_trade_as_processed
from backend.services.telegram_client import send_telegram_alert
from backend.services.binance_client import FUTURES_BASE_URL, generate_signature, get_binance_headers

async def monitor_binance_positions_loop():
    """
    Background loop that polls active positions and orders on Binance Futures.
    Calculates realized P&L when positions are closed and updates dailyStats.
    """
    # Track active positions locally to detect when they close
    # Format: { "symbol": { "entryPrice": float, "quantity": float, "side": str, "orderId": str } }
    active_positions = {}
    
    # Backoff multiplier for rate limits (HTTP 429)
    backoff_delay = 5.0

    while True:
        try:
            config = await load_ai_config()
            api_key = config.get("binanceApiKey", "")
            api_secret = config.get("binanceApiSecret", "")
            dry_run = config.get("dryRun", True)

            if dry_run or not api_key or not api_secret:
                await asyncio.sleep(10)
                continue

            async with httpx.AsyncClient(verify=False) as client:
                # 1. Fetch current open positions from Binance Futures
                timestamp = int(time.time() * 1000)
                query = f"timestamp={timestamp}"
                signature = generate_signature(query, api_secret)
                url = f"{FUTURES_BASE_URL}/fapi/v2/positionRisk?{query}&signature={signature}"
                headers = await get_binance_headers(api_key)

                res = await client.get(url, headers=headers, timeout=10.0)
                
                # Handle Rate Limit (HTTP 429)
                if res.status_code == 429:
                    print(f"[Position Monitor] Rate limit hit (429). Backing off for {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(60.0, backoff_delay * 1.5) # Exponential backoff up to 60s
                    continue
                else:
                    backoff_delay = 5.0 # Reset backoff on success
                    
                if res.status_code == 200:
                    positions_data = res.json()
                    
                    # Filter positions with non-zero size
                    current_active_symbols = set()
                    for pos in positions_data:
                        symbol = pos.get("symbol", "")
                        position_amt = float(pos.get("positionAmt", 0.0))
                        entry_price = float(pos.get("entryPrice", 0.0))
                        
                        if position_amt != 0.0:
                            current_active_symbols.add(symbol)
                            # If this is a new position we haven't tracked yet, start tracking it
                            if symbol not in active_positions:
                                active_positions[symbol] = {
                                    "entryPrice": entry_price,
                                    "quantity": abs(position_amt),
                                    "side": "LONG" if position_amt > 0 else "SHORT"
                                }
                                print(f"[Position Monitor] Started tracking active position: {symbol} {active_positions[symbol]['side']} size {abs(position_amt)}")

                    # 2. Detect closed positions
                    closed_symbols = []
                    for symbol, pos_info in list(active_positions.items()):
                        if symbol not in current_active_symbols:
                            # Position has been closed! Fetch recent trades to get the actual realized P&L
                            closed_symbols.append(symbol)
                            
                            # Query userTrades history (up to 24 hours back to capture trades if backend was offline)
                            one_day_ago = timestamp - (24 * 60 * 60 * 1000)
                            trade_query = f"symbol={symbol}&startTime={one_day_ago}&limit=50&timestamp={timestamp}"
                            trade_sig = generate_signature(trade_query, api_secret)
                            trade_url = f"{FUTURES_BASE_URL}/fapi/v1/userTrades?{trade_query}&signature={trade_sig}"
                            
                            trade_res = await client.get(trade_url, headers=headers, timeout=10.0)
                            if trade_res.status_code == 200:
                                trades = trade_res.json()
                                realized_pnl = 0.0
                                processed_any = False
                                
                                for t in trades:
                                    trade_id = str(t.get("id"))
                                    # Prevent double-counting by checking database tracking
                                    if not await is_trade_processed(trade_id):
                                        realized_pnl += float(t.get("realizedPnl", 0.0))
                                        await mark_trade_as_processed(trade_id)
                                        processed_any = True
                                
                                if processed_any:
                                    # Update daily stats with the actual realized P&L
                                    await update_daily_stats(realized_pnl)
                                    
                                    msg = f"Position Closed: {symbol} | Realized P&L: ${realized_pnl:.2f}"
                                    print(f"[Position Monitor] {msg}")
                                    await send_telegram_alert(msg)
                            else:
                                print(f"[Position Monitor] Failed to fetch trades for closed position {symbol}: {trade_res.text}")

                    # Remove closed positions from tracking
                    for symbol in closed_symbols:
                        active_positions.pop(symbol, None)

        except Exception as e:
            print(f"[Position Monitor] Error in monitor loop: {e}")
            
        await asyncio.sleep(5) # Poll every 5 seconds
