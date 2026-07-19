"""ML model endpoints extracted from main.py."""
import pandas as pd
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.core.logger import logger
from backend.models.schemas import DownloadDataRequest, MLTrainRequest

router = APIRouter()


@router.post("/api/ml/download")
async def download_dataset_endpoint(req: DownloadDataRequest):
    try:
        from backend.services.ml.dataset_updater import update_dataset
        if req.symbol == "ALL":
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "SHIBUSDT", "LTCUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT"]
            results = []
            for sym in symbols:
                res = await update_dataset(sym, req.startDate, req.endDate)
                results.append(res)
            return {"status": "success", "message": f"Updated {len(symbols)} coins.", "details": results}
        else:
            result = await update_dataset(req.symbol, req.startDate, req.endDate)
            return result
    except Exception as e:
        logger.error(f"[ML] Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ml/train")
async def train_ml_model_endpoint(req: MLTrainRequest, background_tasks: BackgroundTasks):
    from backend.config import DB_PATH
    from backend.services.ml.model import train_model
    
    feather_path = DB_PATH.parent / "Train-data" / "BTC_USDT_futures_1m.feather"
    if not feather_path.exists():
        feather_path = DB_PATH.parent / "backend" / "btc_1m.feather"
    
    if not feather_path.exists():
        feather_path = DB_PATH.parent / "backend" / "btc_1m_mock.feather"
        if not feather_path.exists():
            from backend.services.ml.generate_mock_data import generate_mock_feather_data
            generate_mock_feather_data(str(feather_path))
            
    background_tasks.add_task(
        train_model,
        file_path=str(feather_path),
        target_window=req.targetWindow,
        threshold_pct=req.thresholdPct,
        model_type=req.modelType
    )
    
    return { "status": "ok", "message": "Model training started in the background." }


@router.get("/api/ml/metrics")
async def get_ml_metrics():
    from backend.database import db_lock, read_database_async
    async with db_lock:
        db = await read_database_async()
        return db.get("mlMetrics", { "status": "idle" })


@router.post("/api/ml/predict")
async def predict_ml_endpoint(req: Dict[str, Any]):
    from backend.services.ml.evaluator import predict_live
    
    candles = req.get("candles", [])
    if not candles or len(candles) < 30:
        raise HTTPException(status_code=400, detail="At least 30 recent candles are required for feature extraction.")
        
    df_latest = pd.DataFrame(candles)
    from backend.database import load_ai_config
    config = await load_ai_config()
    model_type = config.get("mlModelType", "xgboost")
    
    pred, conf = predict_live(df_latest, model_type=model_type)
    
    return {
        "prediction": int(pred),
        "confidence": float(conf)
    }
