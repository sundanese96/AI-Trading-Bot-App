import time
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.logger import logger

router = APIRouter()

class StartSessionRequest(BaseModel):
    strategy: str
    initialCapital: float
    targetAssets: List[str]
    confidenceThreshold: Optional[int] = 75
    bollingerStdDev: Optional[float] = 2.0

@router.post("/api/live-sim/start")
async def start_live_sim_session(req: StartSessionRequest):
    from backend.services.live_sim_manager import live_sim_manager
    await live_sim_manager.start_session(
        strategy=req.strategy,
        initial_capital=req.initialCapital,
        target_assets=req.targetAssets,
        confidence_threshold=req.confidenceThreshold,
        bollinger_std_dev=req.bollingerStdDev
    )
    logger.info(f"Simulation session started with strategy {req.strategy}")
    return {
        "status": "success",
        "message": f"Simulation session started with strategy {req.strategy}"
    }

@router.post("/api/live-sim/stop")
async def stop_live_sim_session():
    from backend.services.live_sim_manager import live_sim_manager
    await live_sim_manager.stop_session()
    logger.info("Simulation session stopped")
    return {
        "status": "success",
        "message": "Simulation session stopped"
    }

@router.get("/api/live-sim/status")
async def get_live_sim_status():
    from backend.services.live_sim_manager import live_sim_manager
    return {
        "active": live_sim_manager.active,
        "strategy": live_sim_manager.strategy,
        "initialCapital": live_sim_manager.initial_capital,
        "currentCapital": live_sim_manager.current_capital,
        "targetAssets": live_sim_manager.target_assets,
        "confidenceThreshold": getattr(live_sim_manager, "confidence_threshold", 75),
        "bollingerStdDev": getattr(live_sim_manager, "bollinger_std_dev", 2.0),
        "startTime": live_sim_manager.start_time,
        "elapsedTime": time.time() - live_sim_manager.start_time if live_sim_manager.active else 0,
        "logs": live_sim_manager.logs
    }

@router.get("/api/live-sim/trades")
async def get_live_sim_trades():
    from backend.services.live_sim_manager import live_sim_manager
    return live_sim_manager.trades
