import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from backend.services.ml.features import extract_features


def apply_triple_barrier_labels(
    df: pd.DataFrame,
    tp_pct: float = 2.5,
    sl_pct: float = 1.5,
    max_holding: int = 30
) -> Tuple[pd.Series, pd.Series]:
    """
    Triple-Barrier Labeling (Marcos López de Prado methodology).
    
    For each candle at index T, scans forward up to max_holding bars using
    high/low prices to determine which barrier is hit first:
      - Upper Barrier (TP): high >= entry * (1 + tp_pct/100)  →  direction = +1
      - Lower Barrier (SL): low  <= entry * (1 - sl_pct/100)  →  direction = -1
      - Time Barrier (timeout): neither hit within max_holding →  direction =  0
    
    Returns:
      direction_labels: Series of {-1, 0, 1} for primary model training
      meta_labels: Series of {0, 1} where 1 = TP hit first (trade success)
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    
    direction = np.zeros(n, dtype=int)
    meta = np.zeros(n, dtype=int)
    
    for i in range(n - 1):
        entry = close[i]
        tp_price = entry * (1.0 + tp_pct / 100.0)
        sl_price = entry * (1.0 - sl_pct / 100.0)
        
        end_idx = min(i + max_holding, n - 1)
        
        tp_hit_bar = -1
        sl_hit_bar = -1
        
        for j in range(i + 1, end_idx + 1):
            if tp_hit_bar == -1 and high[j] >= tp_price:
                tp_hit_bar = j
            if sl_hit_bar == -1 and low[j] <= sl_price:
                sl_hit_bar = j
            if tp_hit_bar != -1 and sl_hit_bar != -1:
                break
        
        if tp_hit_bar != -1 and sl_hit_bar != -1:
            # Both hit — whoever hit first wins
            if tp_hit_bar <= sl_hit_bar:
                direction[i] = 1   # UP win
                meta[i] = 1
            else:
                direction[i] = -1  # DOWN loss
                meta[i] = 0
        elif tp_hit_bar != -1:
            direction[i] = 1
            meta[i] = 1
        elif sl_hit_bar != -1:
            direction[i] = -1
            meta[i] = 0
        else:
            # Timeout — treat as neutral / no-trade
            direction[i] = 0
            meta[i] = 0
    
    return pd.Series(direction, index=df.index), pd.Series(meta, index=df.index)

def prepare_training_data(
    file_path: str, 
    target_window: int = 15, 
    threshold_pct: float = 0.15,
    resample_minutes: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.Series, Tuple[pd.DataFrame, pd.Series], Tuple[pd.DataFrame, pd.Series], Tuple[pd.DataFrame, pd.Series]]:
    """
    Loads raw BTC 1m data, resamples if specified, calculates features,
    creates classification targets, and splits data chronologically.
    
    Targets:
      1: UP (price change > threshold_pct in target_window candles)
      0: NEUTRAL (price change within threshold_pct)
     -1: DOWN (price change < -threshold_pct in target_window candles)
    """
    # 1. Load raw data (Feather format)
    df = pd.read_feather(file_path)
    
    # Identify datetime column
    date_col = 'date' if 'date' in df.columns else ('timestamp' if 'timestamp' in df.columns else None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
    
    # Perform resampling if requested
    if resample_minutes is not None and resample_minutes > 1:
        if date_col:
            df = df.set_index(date_col)
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            resample_rule = f"{resample_minutes}min"
            df = df.resample(resample_rule).agg(agg_dict).dropna().reset_index()
            print(f"[Data Prep] Resampled 1m candles into {resample_minutes}m candles. Target size: {len(df)}")
        else:
            print("[Data Prep] Warning: Resampling requested but no date/timestamp column found. Skipping resampling.")
            df = df.reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    
    # 2. Calculate features on the entire dataset BEFORE splitting
    # This ensures rolling windows are calculated continuously without boundary leakage
    features_df = extract_features(df)
    
    # 3. Create classification targets
    # Future price change percentage
    future_close = df['close'].shift(-target_window)
    price_change_pct = (future_close - df['close']) / df['close'] * 100
    
    targets = pd.Series(0, index=df.index)
    targets[price_change_pct > threshold_pct] = 1
    targets[price_change_pct < -threshold_pct] = -1
    
    # 4. Clean NaN and Inf values resulting from rolling windows and future shifts
    # Replace inf and -inf with NaN so they get dropped
    features_clean = features_df.replace([np.inf, -np.inf], np.nan)
    valid_idx = features_clean.dropna().index.intersection(price_change_pct.dropna().index)
    
    X = features_clean.loc[valid_idx].reset_index(drop=True)
    y = targets.loc[valid_idx].reset_index(drop=True)
    
    # Print target class distribution (count and percentage)
    class_counts = y.value_counts()
    total_samples = len(y)
    print("\n=== TARGET CLASS DISTRIBUTION ===")
    for cls in [-1, 0, 1]:
        count = class_counts.get(cls, 0)
        pct = (count / total_samples) * 100
        label = "UP" if cls == 1 else ("DOWN" if cls == -1 else "NEUTRAL")
        print(f"- {label} ({cls}): {count} samples ({pct:.2f}%)")
    
    # Recommendation if data is highly imbalanced
    neutral_pct = (class_counts.get(0, 0) / total_samples) * 100
    if neutral_pct > 80.0:
        print("\n[WARNING] Highly imbalanced dataset detected (NEUTRAL > 80%).")
        print("Recommendations:")
        print("1. Adjust 'threshold_pct' to a lower value (e.g., 0.08% - 0.10%) to capture more moves.")
        print("2. Use 'class_weight' parameter in XGBoost/LightGBM during training.")
        print("3. Apply SMOTE or downsampling to balance the classes.")
    
    # 5. Time-Series Split (70% Train, 15% Val, 15% Test)
    n_samples = len(X)
    train_end = int(n_samples * 0.70)
    val_end = int(n_samples * 0.85)
    
    X_train = X.iloc[:train_end]
    y_train = y.iloc[:train_end]
    
    X_val = X.iloc[train_end:val_end]
    y_val = y.iloc[train_end:val_end]
    
    X_test = X.iloc[val_end:]
    y_test = y.iloc[val_end:]
    
    print(f"\n[Data Prep] Total samples: {n_samples}")
    print(f"[Data Prep] Train set: {len(X_train)} samples ({X_train.index[0]} to {X_train.index[-1]})")
    print(f"[Data Prep] Val set: {len(X_val)} samples ({X_val.index[0]} to {X_val.index[-1]})")
    print(f"[Data Prep] Test set: {len(X_test)} samples ({X_test.index[0]} to {X_test.index[-1]})")
    
    return X, y, (X_train, y_train), (X_val, y_val), (X_test, y_test)


def prepare_training_data_v2(
    file_path: str,
    tp_pct: float = 2.5,
    sl_pct: float = 1.5,
    max_holding: int = 30,
    resample_minutes: Optional[int] = None
) -> Dict:
    """
    V2 data preparation using Triple-Barrier labeling.
    
    Returns a dict with:
      - X, y_direction, y_meta: full arrays
      - train, val, test: tuples of (X, y_direction, y_meta)
      - df_clean: the cleaned OHLCV DataFrame (for barrier scanning)
    """
    # 1. Load raw data
    df = pd.read_feather(file_path)
    
    date_col = 'date' if 'date' in df.columns else ('timestamp' if 'timestamp' in df.columns else None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
    
    # Resample if requested
    if resample_minutes is not None and resample_minutes > 1:
        if date_col:
            df = df.set_index(date_col)
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            resample_rule = f"{resample_minutes}min"
            df = df.resample(resample_rule).agg(agg_dict).dropna().reset_index()
            print(f"[Data Prep V2] Resampled to {resample_minutes}m. Size: {len(df)}")
        else:
            df = df.reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    
    # 2. Extract features
    features_df = extract_features(df)
    
    # 3. Apply Triple-Barrier Labels
    print(f"[Data Prep V2] Applying Triple-Barrier Labels (TP={tp_pct}%, SL={sl_pct}%, MaxHold={max_holding} bars)...")
    y_direction, y_meta = apply_triple_barrier_labels(df, tp_pct, sl_pct, max_holding)
    
    # 4. Clean NaN/Inf
    features_clean = features_df.replace([np.inf, -np.inf], np.nan)
    # Valid indices: features must be non-NaN AND we need enough forward bars for barrier scan
    valid_idx = features_clean.dropna().index
    # Exclude last max_holding rows (no room to scan forward)
    valid_idx = valid_idx[valid_idx < len(df) - max_holding]
    
    X = features_clean.loc[valid_idx].reset_index(drop=True)
    y_dir = y_direction.loc[valid_idx].reset_index(drop=True)
    y_met = y_meta.loc[valid_idx].reset_index(drop=True)
    
    # Print class distribution
    total = len(y_dir)
    print(f"\n=== TRIPLE-BARRIER CLASS DISTRIBUTION ===")
    for cls, label in [(-1, 'SL HIT (DOWN)'), (0, 'TIMEOUT (NEUTRAL)'), (1, 'TP HIT (UP)')]:
        count = (y_dir == cls).sum()
        pct = count / total * 100
        print(f"- {label} ({cls}): {count} samples ({pct:.2f}%)")
    
    meta_win = (y_met == 1).sum()
    print(f"\n=== META-LABEL DISTRIBUTION ===")
    print(f"- WIN (TP first): {meta_win} ({meta_win/total*100:.2f}%)")
    print(f"- LOSS (SL/Timeout): {total - meta_win} ({(total-meta_win)/total*100:.2f}%)")
    
    # 5. Chronological split 70/15/15
    n_samples = len(X)
    train_end = int(n_samples * 0.70)
    val_end = int(n_samples * 0.85)
    
    result = {
        'X': X, 'y_direction': y_dir, 'y_meta': y_met,
        'train': (
            X.iloc[:train_end],
            y_dir.iloc[:train_end],
            y_met.iloc[:train_end]
        ),
        'val': (
            X.iloc[train_end:val_end],
            y_dir.iloc[train_end:val_end],
            y_met.iloc[train_end:val_end]
        ),
        'test': (
            X.iloc[val_end:],
            y_dir.iloc[val_end:],
            y_met.iloc[val_end:]
        ),
        'df_clean': df,
        'valid_indices': valid_idx
    }
    
    print(f"\n[Data Prep V2] Total: {n_samples} | Train: {train_end} | Val: {val_end - train_end} | Test: {n_samples - val_end}")
    return result
