from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.live_trading.service import (
    get_binance_account_info,
    get_binance_positions,
    get_binance_open_orders,
    cancel_binance_order,
    close_binance_position,
    execute_futures_order
)

router = APIRouter(prefix="/api/live-trading", tags=["Live Trading"])

class LiveExecuteRequest(BaseModel):
    symbol: str
    side: str
    positionSide: str
    orderType: str
    quantity: float
    leverage: int
    stopLossPct: Optional[float] = None
    takeProfitPct: Optional[float] = None

class LiveCancelRequest(BaseModel):
    symbol: str
    orderId: int

class LiveCloseRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    positionSide: str

@router.get("/account")
async def account_endpoint():
    res = await get_binance_account_info()
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.get("/positions")
async def positions_endpoint():
    return await get_binance_positions()

@router.get("/orders")
async def orders_endpoint():
    return await get_binance_open_orders()

@router.post("/execute")
async def execute_endpoint(req: LiveExecuteRequest):
    # Call execute_futures_order from binance_client service
    res = await execute_futures_order(
        symbol=req.symbol,
        side=req.side,
        position_side=req.positionSide,
        order_type=req.orderType,
        quantity=req.quantity,
        leverage=req.leverage,
        stop_loss_pct=req.stopLossPct,
        take_profit_pct=req.takeProfitPct
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/cancel")
async def cancel_endpoint(req: LiveCancelRequest):
    res = await cancel_binance_order(symbol=req.symbol, order_id=req.orderId)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/close")
async def close_endpoint(req: LiveCloseRequest):
    res = await close_binance_position(
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        position_side=req.positionSide
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res
