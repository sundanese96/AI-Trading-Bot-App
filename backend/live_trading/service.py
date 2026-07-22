import time
import asyncio
from typing import Dict, Any, List
from backend.database import load_ai_config
from backend.services.binance_client import (
    _get_ccxt_client,
    execute_futures_order,
    BINANCE_API_KEY,
    BINANCE_API_SECRET
)

async def get_credentials_and_client():
    config = await load_ai_config()
    api_key = config.get("binanceApiKey", BINANCE_API_KEY)
    api_secret = config.get("binanceApiSecret", BINANCE_API_SECRET)
    
    if not api_key or not api_secret:
        raise ValueError("Binance API Key atau Secret belum dikonfigurasi di Settings.")
        
    return api_key, api_secret

async def get_binance_account_info() -> Dict[str, Any]:
    """
    Fetch account metrics from Binance Futures API (/fapi/v2/account) using CCXT.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        client = _get_ccxt_client(api_key, api_secret)
        
        # ccxt fetch_balance
        bal = await asyncio.to_thread(client.fetch_balance)
        usdt_asset = bal.get("USDT") or {}
        
        # ccxt fetch_positions to sum unrealized profit
        positions = await asyncio.to_thread(client.fetch_positions)
        total_unrealized_profit = sum(float(p.get("unrealizedProfit", 0.0) or 0.0) for p in positions)
        
        wallet_balance = float(usdt_asset.get("total", 0.0) or 0.0)
        available_balance = float(usdt_asset.get("free", 0.0) or 0.0)
        margin_balance = wallet_balance + total_unrealized_profit
        
        return {
            "status": "success",
            "walletBalance": wallet_balance,
            "availableBalance": available_balance,
            "marginBalance": margin_balance,
            "unrealizedProfit": total_unrealized_profit,
            "marginRatio": 0.0,  # CCXT does not return this directly without extra calls, keep it default 0
            "raw": bal
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def get_binance_positions() -> List[Dict[str, Any]]:
    """
    Fetch active positions from Binance Futures API (/fapi/v2/positionRisk) using CCXT.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        client = _get_ccxt_client(api_key, api_secret)
        
        positions = await asyncio.to_thread(client.fetch_positions)
        active = []
        for pos in positions:
            amt = float(pos.get("contracts", 0.0) or 0.0)
            if amt != 0.0:
                active.append({
                    "symbol": pos.get("symbol", ""),
                    "positionAmt": amt,
                    "entryPrice": float(pos.get("entryPrice", 0.0) or 0.0),
                    "markPrice": float(pos.get("markPrice", 0.0) or 0.0),
                    "unrealizedProfit": float(pos.get("unrealizedProfit", 0.0) or 0.0),
                    "leverage": int(pos.get("leverage", 1)),
                    "liquidationPrice": float(pos.get("liquidationPrice", 0.0) or 0.0),
                    "positionSide": pos.get("side", "BOTH").upper(),
                    "marginType": pos.get("marginType", "cross")
                })
        return active
    except Exception as e:
        print(f"[Live Trading] Position fetch exception: {e}")
        return []

async def get_binance_open_orders() -> List[Dict[str, Any]]:
    """
    Fetch active open orders from Binance Futures API (/fapi/v1/openOrders) using CCXT.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        client = _get_ccxt_client(api_key, api_secret)
        
        # CCXT fetch_open_orders
        orders = await asyncio.to_thread(client.fetch_open_orders)
        parsed = []
        for order in orders:
            info = order.get("info", {})
            parsed.append({
                "orderId": order.get("id"),
                "symbol": order.get("symbol"),
                "status": order.get("status"),
                "clientOrderId": order.get("clientOrderId"),
                "price": float(order.get("price", 0.0) or 0.0),
                "avgPrice": float(order.get("average", 0.0) or 0.0),
                "origQty": float(order.get("amount", 0.0) or 0.0),
                "executedQty": float(order.get("filled", 0.0) or 0.0),
                "type": order.get("type"),
                "side": order.get("side"),
                "stopPrice": float(info.get("stopPrice", 0.0) or 0.0),
                "time": order.get("timestamp"),
                "workingType": info.get("workingType"),
                "positionSide": info.get("positionSide", "BOTH")
            })
        return parsed
    except Exception as e:
        print(f"[Live Trading] Open orders exception: {e}")
        return []

async def cancel_binance_order(symbol: str, order_id: int) -> Dict[str, Any]:
    """
    Cancel an active order on Binance Futures (DELETE /fapi/v1/order) using CCXT.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        client = _get_ccxt_client(api_key, api_secret)
        
        # Format symbol for CCXT (e.g. BTC/USDT or BTCUSDT depending on format)
        symbol_formatted = symbol.upper()
        if not "/" in symbol_formatted and symbol_formatted.endswith("USDT"):
            symbol_formatted = symbol_formatted.replace("USDT", "/USDT")
            
        res = await asyncio.to_thread(client.cancel_order, str(order_id), symbol_formatted)
        return {"status": "success", "message": "Order successfully cancelled.", "data": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def close_binance_position(symbol: str, side: str, quantity: float, position_side: str = "BOTH") -> Dict[str, Any]:
    """
    Closes an active position instantly using a MARKET order in the opposite direction via CCXT.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        client = _get_ccxt_client(api_key, api_secret)
        opposite_side = "SELL" if side.upper() == "BUY" or side.upper() == "LONG" else "BUY"
        
        symbol_formatted = symbol.upper()
        if not "/" in symbol_formatted and symbol_formatted.endswith("USDT"):
            symbol_formatted = symbol_formatted.replace("USDT", "/USDT")
            
        # CCXT order creation
        res = await asyncio.to_thread(
            client.create_order,
            symbol_formatted,
            "market",
            opposite_side.lower(),
            quantity,
            params={"positionSide": position_side.upper()}
        )
        return {
            "status": "success",
            "message": f"Successfully closed position for {symbol} with MARKET {opposite_side} order.",
            "data": res
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
