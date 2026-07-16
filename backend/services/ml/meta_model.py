"""
Meta-Model: Secondary binary classifier for trade success prediction.

The meta-model answers: "Given the primary model predicted a directional trade,
what is the probability that this trade will hit Take-Profit before Stop-Loss?"

Training pipeline:
1. Primary model predicts on validation set → get predictions & confidences
2. Filter only directional predictions (UP/DOWN, skip NEUTRAL)
3. For each directional prediction, check triple-barrier outcome (WIN=1, LOSS=0)
4. Train meta-model on: [primary_confidence, primary_prediction, features...] → binary target

The meta-model output is a calibrated probability of trade success.
"""

import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def get_meta_model_path(resample_minutes: Optional[int] = None) -> Path:
    suffix = f"_{resample_minutes}m" if resample_minutes and resample_minutes > 1 else ""
    return MODEL_DIR / f"meta_model{suffix}.txt"


def get_calibrator_path(resample_minutes: Optional[int] = None) -> Path:
    suffix = f"_{resample_minutes}m" if resample_minutes and resample_minutes > 1 else ""
    return MODEL_DIR / f"calibrator{suffix}.pkl"


def train_meta_model(
    primary_model,
    model_type: str,
    X_train: pd.DataFrame,
    y_meta_train: pd.Series,
    X_val: pd.DataFrame,
    y_meta_val: pd.Series,
    X_test: pd.DataFrame,
    y_meta_test: pd.Series,
    resample_minutes: Optional[int] = None,
    num_rounds: int = 300
) -> Dict[str, Any]:
    """
    Trains a LightGBM meta-classifier.
    
    Per de Prado methodology:
    - Train on primary model's TRAIN SET predictions (the primary model has some fit here,
      which is intentional — the meta-model learns which predictions are trustworthy)
    - Early-stop using primary model's VAL SET predictions
    - Evaluate on held-out TEST SET predictions
    
    The meta-model receives:
      - All original features
      - primary_confidence: max probability from primary model
      - primary_pred: predicted direction from primary model (-1, 0, 1)
    
    Target: binary y_meta (1 = TP hit first, 0 = SL hit or timeout)
    """
    import lightgbm as lgb
    
    # 1. Build meta-features for TRAIN set
    print("\n[Meta-Model] Generating primary model predictions on train set...")
    train_probs = _get_probabilities(primary_model, model_type, X_train)
    train_preds = train_probs.argmax(axis=1) - 1
    train_confs = train_probs.max(axis=1)
    
    dir_mask_train = (train_preds != 0)
    X_meta_train = X_train[dir_mask_train].copy()
    X_meta_train['primary_confidence'] = train_confs[dir_mask_train]
    X_meta_train['primary_pred'] = train_preds[dir_mask_train]
    y_meta_tr = y_meta_train[dir_mask_train].reset_index(drop=True)
    X_meta_train = X_meta_train.reset_index(drop=True)
    
    print(f"[Meta-Model] Directional trades in train set: {len(X_meta_train)} / {len(X_train)}")
    print(f"[Meta-Model] Train set win rate: {y_meta_tr.mean():.4f}")
    
    # 2. Build meta-features for VAL set (early stopping)
    print("[Meta-Model] Generating primary model predictions on val set...")
    val_probs = _get_probabilities(primary_model, model_type, X_val)
    val_preds = val_probs.argmax(axis=1) - 1
    val_confs = val_probs.max(axis=1)
    
    dir_mask_val = (val_preds != 0)
    X_meta_val = X_val[dir_mask_val].copy()
    X_meta_val['primary_confidence'] = val_confs[dir_mask_val]
    X_meta_val['primary_pred'] = val_preds[dir_mask_val]
    y_meta_vl = y_meta_val[dir_mask_val].reset_index(drop=True)
    X_meta_val = X_meta_val.reset_index(drop=True)
    
    print(f"[Meta-Model] Directional trades in val set: {len(X_meta_val)} / {len(X_val)}")
    
    # 3. Build meta-features for TEST set (final evaluation)
    test_probs = _get_probabilities(primary_model, model_type, X_test)
    test_preds = test_probs.argmax(axis=1) - 1
    test_confs = test_probs.max(axis=1)
    
    dir_mask_test = (test_preds != 0)
    X_meta_test = X_test[dir_mask_test].copy()
    X_meta_test['primary_confidence'] = test_confs[dir_mask_test]
    X_meta_test['primary_pred'] = test_preds[dir_mask_test]
    y_meta_ts = y_meta_test[dir_mask_test].reset_index(drop=True)
    X_meta_test = X_meta_test.reset_index(drop=True)
    
    # 4. Handle class imbalance
    n_pos = y_meta_tr.sum()
    n_neg = len(y_meta_tr) - n_pos
    scale_weight = n_neg / max(n_pos, 1)
    
    # 5. Train LightGBM binary classifier
    print(f"\n[Meta-Model] Training binary meta-classifier...")
    print(f"  Train samples: {len(X_meta_train)} (win rate: {y_meta_tr.mean():.4f})")
    print(f"  Val samples: {len(X_meta_val)} (win rate: {y_meta_vl.mean():.4f})")
    print(f"  scale_pos_weight: {scale_weight:.2f}")
    
    meta_train_ds = lgb.Dataset(
        X_meta_train, label=y_meta_tr, free_raw_data=False
    )
    meta_eval_ds = lgb.Dataset(
        X_meta_val, label=y_meta_vl, reference=meta_train_ds, free_raw_data=False
    )
    
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.03,
        'feature_fraction': 0.7,
        'bagging_fraction': 0.7,
        'bagging_freq': 5,
        'scale_pos_weight': scale_weight,
        'min_data_in_leaf': 100,
        'verbose': -1,
        'seed': 42,
        'n_jobs': -1
    }
    
    callbacks = [
        lgb.early_stopping(stopping_rounds=30, verbose=True),
        lgb.log_evaluation(period=50)
    ]
    
    meta_model = lgb.train(
        params,
        meta_train_ds,
        num_boost_round=num_rounds,
        valid_sets=[meta_eval_ds],
        valid_names=['val'],
        callbacks=callbacks
    )
    
    # 6. Evaluate on held-out test set
    if len(X_meta_test) > 0:
        test_meta_probs = meta_model.predict(X_meta_test)
        
        # Report at multiple thresholds
        print(f"\n[Meta-Model] === TEST SET EVALUATION ===")
        print(f"  Total directional trades: {len(X_meta_test)}")
        print(f"  Base win rate (no filter): {y_meta_ts.mean():.4f}")
        
        for thresh in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55]:
            approved = test_meta_probs >= thresh
            if approved.sum() > 0:
                filt_wr = y_meta_ts.values[approved].mean()
                filt_n = approved.sum()
            else:
                filt_wr = 0.0
                filt_n = 0
            marker = " ◀ DEFAULT" if thresh == 0.40 else ""
            print(f"  P >= {thresh:.2f}: {filt_n:>6} trades | Win Rate: {filt_wr:.4f}{marker}")
        
        # Primary metrics at default threshold (0.40)
        default_approved = test_meta_probs >= 0.40
        if default_approved.sum() > 0:
            filtered_winrate = y_meta_ts.values[default_approved].mean()
            filtered_trades = int(default_approved.sum())
        else:
            filtered_winrate = 0.0
            filtered_trades = 0
            
        test_preds_binary = (test_meta_probs >= 0.40).astype(int)
        accuracy = (test_preds_binary == y_meta_ts.values).mean()
        precision_val = (test_preds_binary & y_meta_ts.values).sum() / max(test_preds_binary.sum(), 1)
        recall_val = (test_preds_binary & y_meta_ts.values).sum() / max(y_meta_ts.sum(), 1)
    else:
        accuracy = 0.0
        precision_val = 0.0
        recall_val = 0.0
        filtered_winrate = 0.0
        filtered_trades = 0
    
    # 7. Save meta-model
    model_path = get_meta_model_path(resample_minutes)
    meta_model.save_model(str(model_path))
    print(f"\n[Meta-Model] Saved to {model_path}")
    
    # 8. Save metrics
    metrics = {
        'meta_train_directional_trades': int(len(X_meta_train)),
        'meta_train_win_rate': float(y_meta_tr.mean()),
        'meta_val_directional_trades': int(len(X_meta_val)),
        'meta_test_accuracy': float(accuracy),
        'meta_test_precision': float(precision_val),
        'meta_test_recall': float(recall_val),
        'meta_filtered_trades': filtered_trades,
        'meta_filtered_win_rate': float(filtered_winrate),
        'meta_best_iteration': meta_model.best_iteration
    }
    
    metrics_path = MODEL_DIR / f"meta_model_metrics_{resample_minutes or 1}m.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[Meta-Model] Metrics saved to {metrics_path}")
    
    return metrics


def load_meta_model(resample_minutes: Optional[int] = None):
    """Loads the trained meta-model from disk."""
    import lightgbm as lgb
    model_path = get_meta_model_path(resample_minutes)
    if not model_path.exists():
        print(f"[Meta-Model] No meta-model found at {model_path}")
        return None
    return lgb.Booster(model_file=str(model_path))


def predict_meta(
    meta_model,
    primary_model,
    model_type: str,
    latest_features: pd.DataFrame
) -> Tuple[float, bool]:
    """
    Runs meta-model inference on the latest features.
    
    Returns:
      p_win: probability of trade success (0.0 - 1.0)
      approved: whether p_win >= 0.55 threshold
    """
    # Get primary model prediction
    probs = _get_probabilities(primary_model, model_type, latest_features)
    pred = probs.argmax(axis=1) - 1
    conf = probs.max(axis=1)
    
    # If primary predicts NEUTRAL, no trade to evaluate
    if pred[0] == 0:
        return 0.0, False
    
    # Build meta-features
    meta_features = latest_features.copy()
    meta_features['primary_confidence'] = conf
    meta_features['primary_pred'] = pred
    
    # Dynamic feature alignment for meta-model
    if hasattr(meta_model, "feature_name"):
        meta_cols = meta_model.feature_name()
        if meta_cols:
            current_meta_cols = meta_features.columns.tolist()
            if current_meta_cols != meta_cols:
                print(f"[Meta-Model] Aligning features to meta-model expected columns. Model expects {len(meta_cols)}, input has {len(current_meta_cols)}.")
                meta_features = meta_features.reindex(columns=meta_cols, fill_value=0.0)
                
    # Predict trade success probability
    p_win = float(meta_model.predict(meta_features)[0])
    approved = p_win >= 0.55
    
    return p_win, approved


def _get_probabilities(model, model_type: str, X: pd.DataFrame) -> np.ndarray:
    """Helper to get probability matrix from any supported model type."""
    import xgboost as xgb
    
    if model_type.lower() == "lightgbm":
        return model.predict(X)
    elif model_type.lower() == "catboost":
        return model.predict_proba(X)
    else:
        dmatrix = xgb.DMatrix(X)
        return model.predict(dmatrix)
