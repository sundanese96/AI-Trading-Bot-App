import time
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.logger import logger

router = APIRouter()

class SaveTradeRequest(BaseModel):
    trade: Dict[str, Any]

@router.get("/api/analyses")
@router.get("/api/database/analyses")
async def get_database_analyses():
    from backend.database import db_lock, read_database, read_database_async
    async with db_lock:
        db = await read_database_async()
        return db.get("savedAnalyses", [])

@router.post("/api/analyses/clear")
@router.post("/api/database/clear")
async def clear_database_analyses():
    from backend.database import db_lock, read_database, read_database_async, write_database, read_database_async, write_database_async
    async with db_lock:
        db = await read_database_async()
        db["savedAnalyses"] = []
        await write_database_async(db)
    logger.info("Database analyses cleared")
    return { "status": "ok" }

@router.get("/api/trades")
@router.get("/api/database/trades")
async def get_database_trades():
    from backend.database import db_lock, read_database, read_database_async
    async with db_lock:
        db = await read_database_async()
        return db.get("savedTrades", [])

@router.post("/api/trades")
@router.post("/api/database/save-trade")
async def save_trade(req: SaveTradeRequest):
    from backend.database import db_lock, read_database, read_database_async, write_database, read_database_async, write_database_async
    async with db_lock:
        db = await read_database_async()
        if "savedTrades" not in db:
            db["savedTrades"] = []
        trade_data = {
            **req.trade,
            "id": f"trade-{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000)
        }
        db["savedTrades"].insert(0, trade_data)
        db["savedTrades"] = db["savedTrades"][:100]
        await write_database_async(db)
    logger.info(f"Trade saved manually to database: {trade_data.get('id')}")
    return { "status": "ok", "trade": trade_data }
