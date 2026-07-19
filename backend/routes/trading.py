"""Binance trading endpoints extracted from main.py."""
from fastapi import APIRouter, HTTPException

from backend.models.schemas import ExecuteOrderRequest

router = APIRouter()


@router.post("/api/binance/execute")
async def execute_order_endpoint(req: ExecuteOrderRequest):
    from backend.services.binance_client import execute_futures_order
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
