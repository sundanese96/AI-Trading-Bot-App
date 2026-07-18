import time
import httpx
from typing import Dict, Any, List
from backend.database import load_ai_config
from backend.config import VERIFY_SSL
from backend.services.binance_client import (
    FUTURES_BASE_URL,
    generate_signature,
    get_binance_headers,
    execute_futures_order
)

async def get_credentials_and_client():
    config = await load_ai_config()
    api_key = config.get("binanceApiKey", "")
    api_secret = config.get("binanceApiSecret", "")
    
    if not api_key or not api_secret:
        raise ValueError("Binance API Key atau Secret belum dikonfigurasi di Settings.")
        
    return api_key, api_secret

async def get_binance_account_info() -> Dict[str, Any]:
    """
    Fetch account metrics from Binance Futures API (/fapi/v2/account)
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        timestamp = int(time.time() * 1000)
        query = f"timestamp={timestamp}"
        signature = generate_signature(query, api_secret)
        url = f"{FUTURES_BASE_URL}/fapi/v2/account?{query}&signature={signature}"
        headers = await get_binance_headers(api_key)
        
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                usdt_asset = next((a for a in data.get("assets", []) if a.get("asset") == "USDT"), {})
                
                return {
                    "status": "success",
                    "walletBalance": float(usdt_asset.get("walletBalance", 0.0)),
                    "availableBalance": float(usdt_asset.get("availableBalance", 0.0)),
                    "marginBalance": float(usdt_asset.get("marginBalance", 0.0)),
                    "unrealizedProfit": float(data.get("totalUnrealizedProfit", 0.0)),
                    "marginRatio": float(data.get("totalMaintMargin", 0.0)) / (float(data.get("totalMarginBalance", 1.0)) or 1.0) * 100.0,
                    "raw": data
                }
            else:
                return {
                    "status": "error",
                    "message": f"Binance API returned error {res.status_code}: {res.text}"
                }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def get_binance_positions() -> List[Dict[str, Any]]:
    """
    Fetch active positions from Binance Futures API (/fapi/v2/positionRisk)
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        timestamp = int(time.time() * 1000)
        query = f"timestamp={timestamp}"
        signature = generate_signature(query, api_secret)
        url = f"{FUTURES_BASE_URL}/fapi/v2/positionRisk?{query}&signature={signature}"
        headers = await get_binance_headers(api_key)
        
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                positions_data = res.json()
                active = []
                for pos in positions_data:
                    amt = float(pos.get("positionAmt", 0.0))
                    if amt != 0.0:
                        active.append({
                            "symbol": pos.get("symbol", ""),
                            "positionAmt": amt,
                            "entryPrice": float(pos.get("entryPrice", 0.0)),
                            "markPrice": float(pos.get("markPrice", 0.0)),
                            "unrealizedProfit": float(pos.get("unRealizedProfit", 0.0)),
                            "leverage": int(pos.get("leverage", 1)),
                            "liquidationPrice": float(pos.get("liquidationPrice", 0.0)),
                            "positionSide": pos.get("positionSide", "BOTH"),
                            "marginType": pos.get("marginType", "cross")
                        })
                return active
            else:
                print(f"[Live Trading] Failed to fetch position risk: {res.text}")
                return []
    except Exception as e:
        print(f"[Live Trading] Position fetch exception: {e}")
        return []

async def get_binance_open_orders() -> List[Dict[str, Any]]:
    """
    Fetch active open orders from Binance Futures API (/fapi/v1/openOrders)
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        timestamp = int(time.time() * 1000)
        query = f"timestamp={timestamp}"
        signature = generate_signature(query, api_secret)
        url = f"{FUTURES_BASE_URL}/fapi/v1/openOrders?{query}&signature={signature}"
        headers = await get_binance_headers(api_key)
        
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                orders_data = res.json()
                parsed = []
                for order in orders_data:
                    parsed.append({
                        "orderId": order.get("orderId"),
                        "symbol": order.get("symbol"),
                        "status": order.get("status"),
                        "clientOrderId": order.get("clientOrderId"),
                        "price": float(order.get("price", 0.0)),
                        "avgPrice": float(order.get("avgPrice", 0.0)),
                        "origQty": float(order.get("origQty", 0.0)),
                        "executedQty": float(order.get("executedQty", 0.0)),
                        "type": order.get("type"),
                        "side": order.get("side"),
                        "stopPrice": float(order.get("stopPrice", 0.0)),
                        "time": order.get("time"),
                        "workingType": order.get("workingType"),
                        "positionSide": order.get("positionSide", "BOTH")
                    })
                return parsed
            else:
                print(f"[Live Trading] Failed to fetch open orders: {res.text}")
                return []
    except Exception as e:
        print(f"[Live Trading] Open orders exception: {e}")
        return []

async def cancel_binance_order(symbol: str, order_id: int) -> Dict[str, Any]:
    """
    Cancel an active order on Binance Futures (DELETE /fapi/v1/order)
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        timestamp = int(time.time() * 1000)
        query = f"symbol={symbol}&orderId={order_id}&timestamp={timestamp}"
        signature = generate_signature(query, api_secret)
        url = f"{FUTURES_BASE_URL}/fapi/v1/order?{query}&signature={signature}"
        headers = await get_binance_headers(api_key)
        
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.delete(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                return {"status": "success", "message": "Order successfully cancelled.", "data": res.json()}
            else:
                return {"status": "error", "message": f"Failed to cancel order: {res.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def close_binance_position(symbol: str, side: str, quantity: float, position_side: str = "BOTH") -> Dict[str, Any]:
    """
    Closes an active position instantly using a MARKET order in the opposite direction.
    """
    try:
        api_key, api_secret = await get_credentials_and_client()
        opposite_side = "SELL" if side.upper() == "BUY" or side.upper() == "LONG" else "BUY"
        timestamp = int(time.time() * 1000)
        
        query = (
            f"symbol={symbol}&side={opposite_side}&positionSide={position_side}&"
            f"type=MARKET&quantity={quantity}&timestamp={timestamp}"
        )
        signature = generate_signature(query, api_secret)
        payload = f"{query}&signature={signature}"
        headers = await get_binance_headers(api_key)
        url = f"{FUTURES_BASE_URL}/fapi/v1/order"
        
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.post(url, headers=headers, content=payload, timeout=10.0)
            if res.status_code == 200:
                return {
                    "status": "success",
                    "message": f"Successfully closed position for {symbol} with MARKET {opposite_side} order.",
                    "data": res.json()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to close position: {res.text}"
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}