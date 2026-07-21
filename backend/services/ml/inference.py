from pathlib import Path
import json
import time
import httpx
import pandas as pd
import numpy as np
import xgboost as xgb
from typing import Tuple, Dict, Any, List, Optional
from backend.services.ml.model import load_model, MODEL_DIR
from backend.services.ml.features import extract_features
from backend.config import VERIFY_SSL

async def fetch_recent_candles(symbol: str, count: int = 150, interval: str = "5m") -> pd.DataFrame:
    """
    Fetches the most recent candles for a given crypto asset from Binance Futures public API.
    Returns a standard DataFrame with columns: open_time, open, high, low, close, volume, date
    """
    # Force clean target trading symbol
    target = symbol.upper()
    if not target.endswith("USDT") and target != "BTC_USDT":
        target = f"{target}USDT"
        
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={target}&interval={interval}&limit={count}"
    
    print(f"[Inference API] Fetching {count} recent candles for {target} at {interval} from Binance Futures...")
    async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
        resp = await client.get(url, timeout=15.0)
    if resp.status_code != 200:
        raise Exception(f"Binance Futures API error while loading klines: {resp.text}")
        
    data = resp.json()
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    
    # Parse date and convert to flot
    df['date'] = pd.to_datetime(df['open_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    return df

async def fetch_historical_candles_from_binance(symbol: str, end_time_ms: int, count: int = 150, interval: str = "5m") -> pd.DataFrame:
    """
    Fetches historical candles ending exactly at (or before) end_time_ms from Binance Futures public API.
    Used for historical feature extraction during dry run simulations.
    """
    # Force clean target trading symbol
    target = symbol.upper()
    if not target.endswith("USDT") and target != "BTC_USDT":
        target = f"{target}USDT"
        
    # Binance API parameter: endTime (endpoint returns klines before and up to endTime)
    # Subtract 1 ms to prevent including the in-progress candle at the exact end_time_ms boundary
    query_end_time = end_time_ms - 1
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={target}&interval={interval}&limit={count}&endTime={query_end_time}"
    
    print(f"[Inference API] Fetching {count} historical candles for {target} ending at {end_time_ms} (interval {interval}) from Binance Futures...")
    async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
        resp = await client.get(url, timeout=15.0)
    if resp.status_code != 200:
        raise Exception(f"Binance Futures API error while loading historical klines: {resp.text}")
        
    data = resp.json()
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    
    # Parse date and convert to float
    df['date'] = pd.to_datetime(df['open_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    return df

def check_ood_guard(latest_features: pd.DataFrame, resample_minutes: int) -> Tuple[bool, List[str]]:
    """
    Checks if the latest feature row values are within the [1st, 99th] percentile boundaries.
    Returns: is_ood (bool), list of OOD violations (string messages)
    """
    bounds_path = MODEL_DIR / f"training_feature_bounds_{resample_minutes}m.json"
    if not bounds_path.exists():
        print(f"[OOD Guard] Warning: Bounds file {bounds_path} not found. Skipping check.")
        return False, []
        
    with open(bounds_path, "r") as f:
        bounds = json.load(f)
        
    is_ood = False
    violations = []
    
    # Check only the latest row
    row = latest_features.iloc[-1]
    
    for col in latest_features.columns:
        if col in bounds:
            val = float(row[col])
            p1 = bounds[col]["p1"]
            p99 = bounds[col]["p99"]
            
            # Check deviation
            if val < p1 or val > p99:
                is_ood = True
                violations.append(f"{col}={val:.5f} (limits: [{p1:.5f}, {p99:.5f}])")
                
    if is_ood:
        print(f"[OOD Guard] OUT OF DISTRIBUTION DETECTED! Violations ({len(violations)}): {', '.join(violations)}")
    else:
        print("[OOD Guard] Features are values within training bounds distribution.")
        
    return is_ood, violations

def predict_live_with_gate(
    df_latest: pd.DataFrame,
    model_type: str = "lightgbm",
    resample_minutes: int = 5
) -> Tuple[int, float, bool, List[str], Optional[float], bool, bool]:
    """
    Performs feature extraction, checks the OOD Guard boundary, loads the model,
    runs primary inference, then chains to meta-model for trade success probability.
    
    Returns: 
      prediction (-1, 0, 1), confidence (0.0-1.0), 
      is_ood (bool), ood_violations (list),
      meta_p_win (Optional[float]), meta_approved (bool), meta_evaluated (bool)
    """
    # 1. Resample to target timeframe if needed
    df_resampled = df_latest.copy()
    if resample_minutes > 1:
        # Standard pandas resampling matching data_prep.py logic
        df_resampled['date'] = pd.to_datetime(df_resampled['date'])
        df_resampled = df_resampled.drop_duplicates(subset=['date']).set_index('date')
        
        # Ensure we sort chronologically before resampling
        df_resampled = df_resampled.sort_index()
        
        resampled_df = pd.DataFrame()
        resampled_df['open'] = df_resampled['open'].resample(f'{resample_minutes}min').first()
        resampled_df['high'] = df_resampled['high'].resample(f'{resample_minutes}min').max()
        resampled_df['low'] = df_resampled['low'].resample(f'{resample_minutes}min').min()
        resampled_df['close'] = df_resampled['close'].resample(f'{resample_minutes}min').last()
        resampled_df['volume'] = df_resampled['volume'].resample(f'{resample_minutes}min').sum()
        
        # Bring back the date column
        df_resampled = resampled_df.dropna().reset_index()
    
    # 2. Extract features
    features = extract_features(df_resampled)
    
    # Handle NaN/Inf values, similar to data_prep clean logic
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.ffill().bfill()
    
    latest_features = features.iloc[[-1]]
    
    # 3. Check OOD Guard
    is_ood, ood_violations = check_ood_guard(latest_features, resample_minutes)
    
    # 4. Load Primary Model
    model = load_model(model_type, resample_minutes)
    if model is None:
        print(f"[Inference] Warning: Model type {model_type} for timeframe {resample_minutes}m not found on disk.")
        return 0, 0.0, is_ood, ood_violations, None, False, False
        
    # Dynamic feature alignment to match the loaded model's training columns
    model_features = None
    if model_type.lower() == "lightgbm":
        if hasattr(model, "feature_name"):
            model_features = model.feature_name()
    elif model_type.lower() == "catboost":
        if hasattr(model, "feature_names_"):
            model_features = model.feature_names_
    else: # xgboost
        if hasattr(model, "feature_names") and model.feature_names is not None:
            model_features = model.feature_names
 
    if model_features is not None:
        current_cols = latest_features.columns.tolist()
        if current_cols != model_features:
            print(f"[Inference] Aligning latest_features to model expected columns. Model expects {len(model_features)}, input has {len(current_cols)}.")
            latest_features = latest_features.reindex(columns=model_features, fill_value=0.0)
        
    # 5. Primary model prediction
    if model_type.lower() == "lightgbm":
        probs = model.predict(latest_features)[0]
    elif model_type.lower() == "catboost":
        probs = model.predict_proba(latest_features)[0]
    else: # xgboost
        dmatrix = xgb.DMatrix(latest_features)
        probs = model.predict(dmatrix)[0]
        
    pred_class_idx = probs.argmax()
    pred_class = pred_class_idx - 1 # Map [0, 1, 2] back to [-1, 0, 1]
    confidence = float(probs[pred_class_idx])
    
    # 6. Meta-Model Chain (if available and prediction is directional)
    meta_p_win = None
    meta_approved = False
    meta_evaluated = False
    
    if pred_class != 0:  # Only run meta-model for directional predictions
        try:
            from backend.services.ml.meta_model import load_meta_model, predict_meta
            meta_model = load_meta_model(resample_minutes)
            if meta_model is not None:
                p_win_val, meta_approved = predict_meta(
                    meta_model, model, model_type, latest_features
                )
                meta_p_win = p_win_val
                meta_evaluated = True
                print(f"[Inference] Meta-model: P(win)={meta_p_win:.4f}, Approved={meta_approved}")
            else:
                # No meta-model available — approve by default (backwards compatible)
                meta_approved = True
                print("[Inference] No meta-model found, approving by default.")
        except Exception as e:
            print(f"[Inference] Meta-model error: {e}. Approving by default.")
            meta_approved = True
    
    return int(pred_class), confidence, is_ood, ood_violations, meta_p_win, meta_approved, meta_evaluated
