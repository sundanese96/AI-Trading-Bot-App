import os
import time
import xgboost as xgb
import pickle
import numpy as np
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, Optional
from backend.services.ml.data_prep import prepare_training_data, prepare_training_data_v2

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
SCALER_PATH = MODEL_DIR / "scaler.pkl"

# Ensure models directory exists
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def get_model_path(model_type: str, resample_minutes: Optional[int] = None, symbol: Optional[str] = None) -> Path:
    tf_suffix = f"_{resample_minutes}m" if resample_minutes and resample_minutes > 1 else ""
    
    # Enforce asset-specific naming or fallback to global for memecoins/altcoins
    sym_lower = "global"
    if symbol:
        sym_clean = symbol.upper().replace("USDT", "")
        # Main assets have their own models, others use global
        if sym_clean in ["BTC", "ETH", "SOL", "BNB"]:
            sym_lower = sym_clean.lower()
            
    asset_prefix = f"{sym_lower}_"
    
    if model_type.lower() == "lightgbm":
        return MODEL_DIR / f"{asset_prefix}lightgbm_model{tf_suffix}.txt"
    elif model_type.lower() == "catboost":
        return MODEL_DIR / f"{asset_prefix}catboost_model{tf_suffix}.cbm"
    else:
        return MODEL_DIR / f"{asset_prefix}xgboost_model{tf_suffix}.json"

def get_device() -> str:
    """Detects if CUDA GPU is available safely without hard crashes."""
    try:
        import torch
        if not torch.cuda.is_available():
            print("[ML Model] PyTorch reports CUDA is not available. Using CPU.")
            return "cpu"
    except ImportError:
        pass

    try:
        dtrain = xgb.DMatrix([[1.0]], label=[1])
        params = {'device': 'cuda'}
        xgb.train(params, dtrain, num_boost_round=1)
        print("[ML Model] CUDA GPU detected and supported by XGBoost. Using GPU.")
        return "cuda"
    except Exception as e:
        print(f"[ML Model] CUDA GPU not available or not supported ({e}). Falling back to CPU.")
        return "cpu"

def train_model(
    file_path: str,
    target_window: int = 15,
    threshold_pct: float = 0.15,
    num_rounds: int = 100,
    model_type: str = "xgboost",
    resample_minutes: Optional[int] = None,
    symbol: Optional[str] = None,
    use_binary_mode: bool = True,
    tp_multiplier: float = 2.0,
    sl_multiplier: float = 1.0,
    max_holding: int = 15
) -> Dict[str, Any]:
    """
    Trains an XGBoost, LightGBM, or CatBoost Classifier on the prepared training data.
    Saves the trained model and evaluation metrics.
    
    By default (use_binary_mode=True), uses Dynamic ATR Triple-Barrier labeling
    for binary classification (LONG vs SHORT), which achieves higher accuracy.
    """
    print(f"[ML Model] Starting model training pipeline ({model_type.upper()}) for asset {symbol or 'GLOBAL'} at timeframe {resample_minutes or 1}m...")
    
    try:
        # 1. Prepare data
        if use_binary_mode:
            # Use V2 with dynamic ATR triple-barrier labeling
            data = prepare_training_data_v2(
                file_path, tp_multiplier, sl_multiplier, max_holding, resample_minutes=resample_minutes
            )
            X_train = data['train'][0]
            y_train = data['train'][1]  # Still [-1, 0, 1] from v2
            X_val = data['val'][0]
            y_val = data['val'][1]
            X_test = data['test'][0]
            y_test = data['test'][1]
            
            # Filter out NEUTRAL samples (0) and convert to binary [0, 1]
            # y_train is [-1, 0, 1] from Triple-Barrier labeling
            train_mask = y_train != 0
            val_mask = y_val != 0
            test_mask = y_test != 0
            
            X_train_binary = X_train[train_mask].reset_index(drop=True)
            # Convert: -1 (SL HIT/DOWN) → 0, 1 (TP HIT/UP) → 1
            # y_train is a pandas Series, so np.where returns a numpy array. Wrap it back into a pandas Series or just use pandas directly.
            y_train_binary = pd.Series(np.where(y_train[train_mask] == -1, 0, 1), dtype=int).reset_index(drop=True)
            
            X_val_binary = X_val[val_mask].reset_index(drop=True)
            y_val_binary = pd.Series(np.where(y_val[val_mask] == -1, 0, 1), dtype=int).reset_index(drop=True)
            
            X_test_binary = X_test[test_mask].reset_index(drop=True)
            y_test_binary = pd.Series(np.where(y_test[test_mask] == -1, 0, 1), dtype=int).reset_index(drop=True)
            
            # Use binary data for training
            X_train, y_train = X_train_binary, y_train_binary
            X_val, y_val = X_val_binary, y_val_binary
            X_test, y_test = X_test_binary, y_test_binary
            
            print(f"[ML Model] Binary mode: Filtered out {len(y_train) - len(X_train_binary)} NEUTRAL samples. Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
        else:
            _, _, train, val, test = prepare_training_data(
                file_path, target_window, threshold_pct, resample_minutes=resample_minutes
            )
            X_train, y_train = train
            X_val, y_val = val
            X_test, y_test = test
        
        # Calculate training feature percentiles for OOD Guard
        bounds = {}
        for col in X_train.columns:
            p1 = float(np.percentile(X_train[col].dropna(), 1))
            p99 = float(np.percentile(X_train[col].dropna(), 99))
            bounds[col] = {"p1": p1, "p99": p99}
            
        sym_lower = "global"
        if symbol:
            sym_clean = symbol.upper().replace("USDT", "")
            if sym_clean in ["BTC", "ETH", "SOL", "BNB"]:
                sym_lower = sym_clean.lower()
                
        bounds_path = MODEL_DIR / f"{sym_lower}_training_feature_bounds_{resample_minutes or 1}m.json"
        with open(bounds_path, "w") as f:
            json.dump(bounds, f, indent=2)
        print(f"[ML Model] Feature percentiles (1st and 99th) saved to {bounds_path}")
        
        # Map targets based on mode
        if use_binary_mode:
            # Binary: y is already 0/1 (SHORT/LONG)
            y_train_mapped = y_train
            y_val_mapped = y_val
            y_test_mapped = y_test
            # Do not set num_class for binary in XGBoost/LightGBM
            num_classes = None
        else:
            # Multiclass: map from [-1, 0, 1] to [0, 1, 2]
            y_train_mapped = y_train + 1
            y_val_mapped = y_val + 1
            y_test_mapped = y_test + 1
            num_classes = 3
        
        # Calculate inverse frequency weights
        class_counts = y_train_mapped.value_counts()
        total_samples = len(y_train_mapped)
        weights = {cls: total_samples / (len(class_counts) * count) for cls, count in class_counts.items()}
        sample_weights = y_train_mapped.map(weights)
        
        # Downweight gradient influence during extreme volatility periods (top 1% highest atr_pct_14)
        if 'atr_pct_14' in X_train.columns:
            threshold_val = np.percentile(X_train['atr_pct_14'].dropna(), 99)
            is_extreme = X_train['atr_pct_14'] > threshold_val
            regime_multiplier = np.where(is_extreme, 0.1, 1.0)
            sample_weights = sample_weights * regime_multiplier
            print(f"[ML Model] Extremely volatile samples (top 1% ATR > {threshold_val:.4f}) downweighted to 0.1 coefficient.")
            
        model_save_path = get_model_path(model_type, resample_minutes, symbol)
        
        if model_type.lower() == "lightgbm":
            import lightgbm as lgb
            
            # Configure parameters
            params = {
                'objective': 'binary' if use_binary_mode else 'multiclass',
                'metric': 'binary_logloss' if use_binary_mode else 'multi_logloss',
                'boosting_type': 'gbdt',
                'learning_rate': 0.03,
                'num_leaves': 31,
                'max_depth': 6,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'random_state': 42
            }
            if not use_binary_mode:
                params['num_class'] = num_classes
            
            # Create Dataset
            train_data = lgb.Dataset(X_train, label=y_train_mapped, weight=sample_weights)
            val_data = lgb.Dataset(X_val, label=y_val_mapped, reference=train_data)
            
            # Train model with early stopping
            print(f"[ML Model] Training LightGBM model for {num_rounds} rounds...")
            gbm = lgb.train(
                params,
                train_data,
                num_boost_round=num_rounds,
                valid_sets=[train_data, val_data],
                callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
            )
            
            # Save Model
            gbm.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # Evaluate on test set
            preds_prob = gbm.predict(X_test)
            if use_binary_mode:
                preds = (preds_prob >= 0.5).astype(int)
            else:
                preds = preds_prob.argmax(axis=1) - 1
            device = "cpu"
            
        elif model_type.lower() == "catboost":
            from catboost import CatBoostClassifier
            
            # Detect GPU device check for CatBoost
            task_type = "CPU"
            try:
                test_model = CatBoostClassifier(iterations=1, task_type="GPU", random_seed=42, verbose=False)
                test_model.fit([[1.0]], [1])
                print("[ML Model] CUDA GPU detected and supported by CatBoost. Using GPU.")
                task_type = "GPU"
            except Exception as e:
                print(f"[ML Model] CatBoost CUDA GPU not available ({e}). Falling back to CPU task_type.")
                task_type = "CPU"
            
            # Configure and train model with early stopping
            print(f"[ML Model] Training CatBoost model on {task_type} for {num_rounds} rounds...")
            model = CatBoostClassifier(
                iterations=num_rounds,
                learning_rate=0.03,
                depth=6,
                loss_function='Logloss' if use_binary_mode else 'MultiClass',
                eval_metric='Logloss' if use_binary_mode else 'MultiClass',
                random_seed=42,
                task_type=task_type,
                verbose=False
            )
            model.fit(
                X_train, y_train_mapped,
                sample_weight=sample_weights,
                eval_set=(X_val, y_val_mapped),
                early_stopping_rounds=15,
                verbose=False
            )
            
            # Save Model
            model.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # Evaluate on test set
            if use_binary_mode:
                preds_prob = model.predict_proba(X_test)
                preds = (preds_prob[:, 1] >= 0.5).astype(int)
            else:
                preds_prob = model.predict_proba(X_test)
                preds = preds_prob.argmax(axis=1) - 1
            device = task_type.lower()
            
        else: # Default: xgboost
            # Detect device (GPU/CPU)
            device = get_device()
            
            # Configure XGBoost parameters
            params = {
                'objective': 'binary:logistic' if use_binary_mode else 'multi:softprob',
                'eval_metric': 'logloss' if use_binary_mode else 'mlogloss',
                'device': device,
                'max_depth': 6,
                'learning_rate': 0.03,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            }
            if not use_binary_mode:
                params['num_class'] = num_classes
            
            # Create DMatrix
            dtrain = xgb.DMatrix(X_train, label=y_train_mapped, weight=sample_weights)
            dval = xgb.DMatrix(X_val, label=y_val_mapped)
            dtest = xgb.DMatrix(X_test, label=y_test_mapped)
            
            # Train model with early stopping
            evals = [(dtrain, 'train'), (dval, 'val')]
            print(f"[ML Model] Training XGBoost model for {num_rounds} rounds...")
            
            bst = xgb.train(
                params,
                dtrain,
                num_boost_round=num_rounds,
                evals=evals,
                early_stopping_rounds=15,
                verbose_eval=False
            )
            
            # Save model checkpoint
            bst.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # Evaluate on test set
            if use_binary_mode:
                preds_prob = bst.predict(dtest)
                preds = (preds_prob >= 0.5).astype(int)
            else:
                preds_prob = bst.predict(dtest)
                preds = preds_prob.argmax(axis=1) - 1 # Map back to [-1, 0, 1]
            
        # Common Evaluation
        from backend.services.ml.evaluator import evaluate_model_performance
        
        trained_model_obj = None
        if model_type.lower() == "lightgbm":
            trained_model_obj = gbm
        elif model_type.lower() == "catboost":
            trained_model_obj = model
        else:
            trained_model_obj = bst
            
        detailed_metrics = evaluate_model_performance(
            X_train, y_train, X_val, y_val, X_test, y_test, trained_model_obj
        )
        
        metrics = {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "device": device,
            "model_type": model_type,
            "resample_minutes": resample_minutes,
            "use_binary_mode": use_binary_mode,
            **detailed_metrics
        }
        
        # Save metrics to database/config
        from backend.database import read_database, write_database
        db = read_database()
        db["mlMetrics"] = metrics
        write_database(db)
        
        return metrics
        
    except Exception as e:
        error_msg = f"Training failed: {str(e)}"
        print(f"[ML Model] ERROR: {error_msg}")
        
        # Save error status
        from backend.database import read_database, write_database
        db = read_database()
        db["mlMetrics"] = {
            "status": "error",
            "error": error_msg,
            "timestamp": int(time.time() * 1000),
            "model_type": model_type,
            "resample_minutes": resample_minutes
        }
        write_database(db)
        
        raise e

def load_model(model_type: str = "xgboost", resample_minutes: Optional[int] = None, symbol: Optional[str] = None) -> Optional[Any]:
    """Loads the trained ML model (XGBoost, LightGBM, or CatBoost) from disk."""
    model_path = get_model_path(model_type, resample_minutes, symbol)
    if model_type.lower() == "lightgbm":
        if not model_path.exists():
            return None
        import lightgbm as lgb
        return lgb.Booster(model_file=str(model_path))
    elif model_type.lower() == "catboost":
        if not model_path.exists():
            return None
        from catboost import CatBoostClassifier
        model = CatBoostClassifier()
        model.load_model(str(model_path))
        return model
    else: # Default/xgboost
        if not model_path.exists():
            return None
        bst = xgb.Booster()
        bst.load_model(str(model_path))
        return bst
