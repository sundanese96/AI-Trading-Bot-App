import sys
import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.metrics import classification_report

FEATHER_PATH = Path("/media/sun/DATA/sentix-ai-crypto-simulator/Train-data/BTCUSDT_5m.feather")

def calculate_rsi_v2(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))

def extract_advanced_features_v2(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    close = df['close']
    
    # 1. Autoregressive price returns (Lags)
    features['return_1'] = close.pct_change(1)
    features['return_2'] = close.pct_change(2)
    features['return_3'] = close.pct_change(3)
    features['return_5'] = close.pct_change(5)
    
    # 2. Moving Average ratios
    features['ma10_ratio'] = (close - close.rolling(10).mean()) / (close.rolling(10).mean() + 1e-9)
    features['ma30_ratio'] = (close - close.rolling(30).mean()) / (close.rolling(30).mean() + 1e-9)
    
    # 3. Normalized Volatility (ATR)
    hl = df['high'] - df['low']
    hc = np.abs(df['high'] - close.shift(1))
    lc = np.abs(df['low'] - close.shift(1))
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()
    features['atr_pct'] = atr / (close + 1e-9)
    
    # 4. Bollinger Bands Z-score
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    features['bb_zscore'] = (close - ma20) / (std20 + 1e-9)
    
    # 5. Momentum (MACD)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    features['macd_hist_ratio'] = (macd - macd_signal) / (close + 1e-9)
    
    # 6. Trend strength (RSI & ADX-like DX indicators)
    features['rsi_14'] = calculate_rsi_v2(close, 14)
    
    # 7. Volume spikes
    vol_sma20 = df['volume'].rolling(20).mean()
    features['volume_ratio'] = df['volume'] / (vol_sma20 + 1e-9)
    
    # 8. Fourier Transform features (DFT frequency components of recent 30 prices)
    try:
        close_vals = close.values
        fft_real_5 = np.zeros(len(df))
        fft_imag_5 = np.zeros(len(df))
        # Sliding window Fourier extraction (heavy calculation, optimized)
        for idx in range(30, len(df)):
            window = close_vals[idx-30:idx]
            fft_coeffs = np.fft.fft(window)
            fft_real_5[idx] = np.real(fft_coeffs[2]) # extract low frequency cycle component
            fft_imag_5[idx] = np.imag(fft_coeffs[2])
        features['fft_real'] = fft_real_5
        features['fft_imag'] = fft_imag_5
    except Exception:
        features['fft_real'] = 0.0
        features['fft_imag'] = 0.0
        
    return features.fillna(0.0)

def get_binary_labels(df: pd.DataFrame, max_holding: int = 15) -> tuple:
    """
    Binary Labeling (TP vs SL). Neutral entries are filtered out.
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    hl = df['high'] - df['low']
    hc = np.abs(df['high'] - df['close'].shift(1))
    lc = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().values
    
    n = len(df)
    labels = np.zeros(n, dtype=int)
    is_valid = np.zeros(n, dtype=bool) # to identify non-neutral entries
    
    for i in range(n - 1):
        entry = close[i]
        curr_atr = atr[i]
        if np.isnan(curr_atr) or curr_atr <= 0:
            curr_atr = entry * 0.001
            
        tp_price = entry + (2.0 * curr_atr)
        sl_price = entry - (1.0 * curr_atr)
        
        end_idx = min(i + max_holding, n - 1)
        tp_hit = -1
        sl_hit = -1
        
        for j in range(i + 1, end_idx + 1):
            if tp_hit == -1 and high[j] >= tp_price:
                tp_hit = j
            if sl_hit == -1 and low[j] <= sl_price:
                sl_hit = j
            if tp_hit != -1 and sl_hit != -1:
                break
                
        if tp_hit != -1 and sl_hit != -1:
            labels[i] = 1 if tp_hit <= sl_hit else 0 # 1 = LONG (win), 0 = SHORT (loss)
            is_valid[i] = True
        elif tp_hit != -1:
            labels[i] = 1
            is_valid[i] = True
        elif sl_hit != -1:
            labels[i] = 0
            is_valid[i] = True
        else:
            labels[i] = 0 # timeout, not valid for binary modeling
            is_valid[i] = False
            
    return pd.Series(labels, index=df.index), pd.Series(is_valid, index=df.index)

def get_multiclass_labels(df: pd.DataFrame, max_holding: int = 15) -> pd.Series:
    """
    Multiclass Labeling using dynamic Triple Barrier ATR bands.
    Returns Series with values: -1 (SL hit), 0 (Timeout/Neutral), 1 (TP hit).
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    hl = df['high'] - df['low']
    hc = np.abs(df['high'] - df['close'].shift(1))
    lc = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().values
    
    n = len(df)
    labels = np.zeros(n, dtype=int)
    
    for i in range(n - 1):
        entry = close[i]
        curr_atr = atr[i]
        if np.isnan(curr_atr) or curr_atr <= 0:
            curr_atr = entry * 0.001
            
        tp_price = entry + (2.0 * curr_atr)
        sl_price = entry - (1.0 * curr_atr)
        
        end_idx = min(i + max_holding, n - 1)
        tp_hit = -1
        sl_hit = -1
        
        for j in range(i + 1, end_idx + 1):
            if tp_hit == -1 and high[j] >= tp_price:
                tp_hit = j
            if sl_hit == -1 and low[j] <= sl_price:
                sl_hit = j
            if tp_hit != -1 and sl_hit != -1:
                break
                
        if tp_hit != -1 and sl_hit != -1:
            labels[i] = 1 if tp_hit <= sl_hit else -1
        elif tp_hit != -1:
            labels[i] = 1
        elif sl_hit != -1:
            labels[i] = -1
        else:
            labels[i] = 0
            
    return pd.Series(labels, index=df.index)

def train_and_eval_binary_vs_multiclass(tf: int):
    # 1. Load & Resample
    df = pd.read_feather(FEATHER_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').set_index('date')
    
    agg_dict = {'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}
    df_res = df.resample(f'{tf}min').agg(agg_dict).dropna().reset_index()
    
    # Extract Features
    X_raw = extract_advanced_features_v2(df_res)
    
    # Clean last rows (no room to scan barrier forward)
    valid_range = X_raw.index[:-15]
    X_raw = X_raw.loc[valid_range]
    
    # ==========================================
    # RUN 1: MULTICLASS MODEL PERFORMANCE (Baseline)
    # ==========================================
    # Calculate Multiclass labels (-1, 0, 1)
    y_multi = get_multiclass_labels(df_res).loc[valid_range]
    
    n_multi = len(X_raw)
    mc_train_end = int(n_multi * 0.70)
    mc_val_end = int(n_multi * 0.85)
    
    X_mc_train, y_mc_train = X_raw.iloc[:mc_train_end], y_multi.iloc[:mc_train_end]
    X_mc_test, y_mc_test = X_raw.iloc[mc_val_end:], y_multi.iloc[mc_val_end:]
    
    mc_model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, random_state=42, verbose=-1)
    mc_model.fit(X_mc_train, y_mc_train + 1) # shift classes to [0,1,2]
    mc_preds = mc_model.predict(X_mc_test) - 1
    mc_rep = classification_report(y_mc_test, mc_preds, output_dict=True, zero_division=0)
    mc_acc = mc_rep['accuracy']
    
    # ==========================================
    # RUN 2: BINARY MODEL PERFORMANCE (Omit Neutral)
    # ==========================================
    y_bin, is_valid = get_binary_labels(df_res)
    y_bin = y_bin.loc[valid_range]
    is_valid = is_valid.loc[valid_range]
    
    # Filter out neutral index samples
    X_bin_filtered = X_raw[is_valid].reset_index(drop=True)
    y_bin_filtered = y_bin[is_valid].reset_index(drop=True)
    
    n_bin = len(X_bin_filtered)
    if n_bin < 10:
        print(f"\nTimeframe: {tf}m | Too few samples for binary model ({n_bin}). Skipping.")
        return
        
    bin_train_end = int(n_bin * 0.70)
    bin_val_end = int(n_bin * 0.85)
    
    X_bin_train, y_bin_train = X_bin_filtered.iloc[:bin_train_end], y_bin_filtered.iloc[:bin_train_end]
    X_bin_test, y_bin_test = X_bin_filtered.iloc[bin_val_end:], y_bin_filtered.iloc[bin_val_end:]
    
    # Train binary models
    print(f"\nTimeframe: {tf}m | Binary Samples: {len(X_bin_filtered)} | Multiclass Samples: {n_multi}")
    print(f"  ├─ Binary Class Balance: LONG (1): {(y_bin_filtered==1).sum()}, SHORT (0): {(y_bin_filtered==0).sum()}")
    
    # Calculate scale_pos_weight for binary models (ratio of negative to positive class)
    n_short = int((y_bin_train == 0).sum())
    n_long = int((y_bin_train == 1).sum())
    pos_scale_weight = float(n_short) / float(n_long) if n_long > 0 else 1.0
    
    for name in ["xgboost", "lightgbm", "catboost"]:
        if name == "xgboost":
            model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, scale_pos_weight=pos_scale_weight, random_state=42)
        elif name == "lightgbm":
            model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, scale_pos_weight=pos_scale_weight, random_state=42, verbose=-1)
        else:
            model = CatBoostClassifier(iterations=100, depth=4, learning_rate=0.03, scale_pos_weight=pos_scale_weight, random_seed=42, verbose=0)
            
        model.fit(X_bin_train, y_bin_train)
        preds = model.predict(X_bin_test)
        if preds.ndim > 1:
            preds = preds.ravel()
            
        rep = classification_report(y_bin_test, preds, output_dict=True, zero_division=0)
        bin_acc = rep['accuracy']
        bin_f1 = rep['macro avg']['f1-score']
        
        print(f"  ├─ [{name.upper()}] Binary Accuracy: {bin_acc:.4f} | F1: {bin_f1:.4f}")
        
    print(f"  └─ [BASELINE MULTICLASS LGBM ACCURACY] : {mc_acc:.4f}")

if __name__ == "__main__":
    if not FEATHER_PATH.exists():
        print(f"Feather data not found at {FEATHER_PATH}")
        sys.exit(1)
        
    print("="*80)
    print(" COMPARATIVE MODEL AUDIT: MULTICLASS VS BINARY CLASSIFIER ")
    print("="*80)
    
    for tf in [5, 15, 60, 180]:
        train_and_eval_binary_vs_multiclass(tf)
