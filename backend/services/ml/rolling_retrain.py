"""
Automatic Rolling Walk-Forward Retraining Service for Sentix V2.
Periodically fetches the latest 30 days of 5m/15m OHLCV candle data directly from Binance Futures,
calculates V2 features + microstructure proxies, and retrains machine learning models
to prevent silent model performance degradation across regime shifts.
"""
import os
import time
import asyncio
import pandas as pd
from pathlib import Path
from backend.core.logger import logger
from backend.services.ml.inference import fetch_recent_candles
from backend.services.ml.model import train_model

SYMBOLS = ["BTC", "ETH", "SOL", "BNB"]
TIMEFRAMES = [5, 15]
MODEL_TYPES = ["lightgbm", "xgboost"]

async def run_rolling_walk_forward_retrain():
    """
    Executes rolling window retraining for all active assets on 5m and 15m timeframes.
    """
    logger.info("[Rolling Retrain] Starting daily walk-forward model retraining cycle...")
    
    for sym in SYMBOLS:
        symbol_usdt = f"{sym}USDT"
        for tf in TIMEFRAMES:
            try:
                # Fetch recent 2000 candles (~7 days of 5m data) live from Binance Futures
                df_recent = await fetch_recent_candles(sym, count=2000, interval=f"{tf}m")
                if df_recent.empty or len(df_recent) < 500:
                    logger.warning(f"[Rolling Retrain] Insufficient candle data for {sym} {tf}m. Skipping.")
                    continue
                    
                # Save temp rolling dataset feather
                temp_feather = f"/tmp/rolling_{sym}_{tf}m.feather"
                df_recent.reset_index(drop=True).to_feather(temp_feather)
                
                for m_type in MODEL_TYPES:
                    try:
                        logger.info(f"[Rolling Retrain] Retraining {sym} {m_type.upper()} ({tf}m) on fresh 7-day rolling window...")
                        train_model(
                            temp_feather,
                            target_window=15,
                            threshold_pct=0.15,
                            num_rounds=80,
                            model_type=m_type,
                            resample_minutes=tf,
                            symbol=sym,
                            use_binary_mode=True
                        )
                    except Exception as train_err:
                        logger.error(f"[Rolling Retrain] Failed training {sym} {m_type} {tf}m: {train_err}")
                        
            except Exception as e:
                logger.error(f"[Rolling Retrain] Error fetching/preparing {sym} {tf}m: {e}")
                
    logger.info("[Rolling Retrain] Completed rolling walk-forward model retraining cycle!")

async def rolling_retrain_background_loop(interval_hours: int = 24):
    """
    Background loop that runs the rolling retraining every N hours (default 24h).
    """
    logger.info(f"[Rolling Retrain Daemon] Started background daemon. Interval: {interval_hours} hours.")
    while True:
        try:
            # Wait 24 hours between runs
            await asyncio.sleep(interval_hours * 3600)
            await run_rolling_walk_forward_retrain()
        except Exception as loop_err:
            logger.error(f"[Rolling Retrain Daemon] Exception in loop: {loop_err}")
            await asyncio.sleep(300)
