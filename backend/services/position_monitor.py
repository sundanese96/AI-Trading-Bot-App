import asyncio
import time
from backend.database import load_ai_config, update_daily_stats, is_trade_processed, mark_trade_as_processed
from backend.services.telegram_client import send_telegram_alert
from backend.services.binance_client import _get_ccxt_client, BINANCE_API_KEY, BINANCE_API_SECRET

async def monitor_binance_positions_loop():
    """
    Background loop that polls active positions and orders on Binance Futures via CCXT.
    Calculates realized P&L when positions are closed and updates dailyStats.
    """
    active_positions = {}
    backoff_delay = 5.0

    while True:
        try:
            config = await load_ai_config()
            api_key = config.get("binanceApiKey", BINANCE_API_KEY)
            api_secret = config.get("binanceApiSecret", BINANCE_API_SECRET)
            dry_run = config.get("dryRun", True)

            if dry_run or not api_key or not api_secret:
                await asyncio.sleep(10)
                continue

            client = _get_ccxt_client(api_key, api_secret)

            # 1. Fetch current open positions from Binance Futures via CCXT
            try:
                positions_data = await asyncio.to_thread(client.fetch_positions)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    print(f"[Position Monitor] Rate limit hit. Backing off for {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(60.0, backoff_delay * 1.5)
                    continue
                raise
            
            backoff_delay = 5.0  # Reset on success

            current_active_symbols = set()
            for pos in positions_data:
                symbol = pos.get("symbol", "")
                contracts = float(pos.get("contracts", 0.0) or 0.0)
                entry_price = float(pos.get("entryPrice", 0.0) or 0.0)
                side = pos.get("side", "")

                if contracts != 0.0:
                    current_active_symbols.add(symbol)
                    if symbol not in active_positions:
                        active_positions[symbol] = {
                            "entryPrice": entry_price,
                            "quantity": abs(contracts),
                            "side": side.upper() if side else ("LONG" if contracts > 0 else "SHORT")
                        }
                        print(f"[Position Monitor] Started tracking active position: {symbol} {active_positions[symbol]['side']} size {abs(contracts)}")

            # 2. Detect closed positions
            closed_symbols = []
            for symbol, pos_info in list(active_positions.items()):
                if symbol not in current_active_symbols:
                    closed_symbols.append(symbol)

                    # Query userTrades via CCXT
                    try:
                        since = int((time.time() - 86400) * 1000)  # 24h ago
                        trades = await asyncio.to_thread(client.fetch_my_trades, symbol, since, 50)
                        realized_pnl = 0.0
                        processed_any = False

                        for t in trades:
                            trade_id = str(t.get("id", ""))
                            if not await is_trade_processed(trade_id):
                                info = t.get("info", {})
                                realized_pnl += float(info.get("realizedPnl", 0.0))
                                await mark_trade_as_processed(trade_id)
                                processed_any = True

                        if processed_any:
                            await update_daily_stats(realized_pnl)
                            msg = f"Position Closed: {symbol} | Realized P&L: ${realized_pnl:.2f}"
                            print(f"[Position Monitor] {msg}")
                            await send_telegram_alert(msg)
                    except Exception as trade_err:
                        print(f"[Position Monitor] Failed to fetch trades for closed position {symbol}: {trade_err}")

            # Remove closed positions from tracking
            for symbol in closed_symbols:
                active_positions.pop(symbol, None)

        except Exception as e:
            print(f"[Position Monitor] Error in monitor loop: {e}")

        await asyncio.sleep(5)
