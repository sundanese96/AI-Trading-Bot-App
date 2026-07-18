import os
import time
import xgboost as xgb
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
from backend.services.ml.data_prep import prepare_training_data

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
SCALER_PATH = MODEL_DIR / "scaler.pkl"

# Ensure models directory exists
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def get_model_path(model_type: str, resample_minutes: Optional[int] = None) -> Path:
    tf_suffix = f"_{resample_minutes}m" if resample_minutes and resample_minutes > 1 else ""
    if model_type.lower() == "lightgbm":
        return MODEL_DIR / f"lightgbm_model{tf_suffix}.txt"
    elif model_type.lower() == "catboost":
        return MODEL_DIR / f"catboost_model{tf_suffix}.cbm"
    else:
        return MODEL_DIR / f"xgboost_model{tf_suffix}.json"

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
    resample_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Trains an XGBoost, LightGBM, or CatBoost Classifier on the prepared training data.
    Saves the trained model and evaluation metrics.
    """
    print(f"[ML Model] Starting model training pipeline ({model_type.upper()}) at timeframe {resample_minutes or 1}m...")
    
    try:
        # 1. Prepare data
        _, _, train, val, test = prepare_training_data(
            file_path, target_window, threshold_pct, resample_minutes=resample_minutes
        )
        X_train, y_train = train
        X_val, y_val = val
        X_test, y_test = test
        
        # Calculate training feature percentiles for OOD Guard
        import numpy as np
        import json
        bounds = {}
        for col in X_train.columns:
            p1 = float(np.percentile(X_train[col].dropna(), 1))
            p99 = float(np.percentile(X_train[col].dropna(), 99))
            bounds[col] = {"p1": p1, "p99": p99}
            
        bounds_path = MODEL_DIR / f"training_feature_bounds_{resample_minutes or 1}m.json"
        with open(bounds_path, "w") as f:
            json.dump(bounds, f, indent=2)
        print(f"[ML Model] Feature percentiles (1st and 99th) saved to {bounds_path}")
        
        # Map targets from [-1, 0, 1] to [0, 1, 2] for multiclass classification
        y_train_mapped = y_train + 1
        y_val_mapped = y_val + 1
        y_test_mapped = y_test + 1
        
        # Calculate inverse frequency weights
        class_counts = y_train.value_counts()
        total_samples = len(y_train)
        weights = {cls: total_samples / (len(class_counts) * count) for cls, count in class_counts.items()}
        sample_weights = y_train.map(weights)
        
        # Downweight gradient influence during extreme volatility periods (top 1% highest atr_pct_14)
        if 'atr_pct_14' in X_train.columns:
            threshold_val = np.percentile(X_train['atr_pct_14'].dropna(), 99)
            is_extreme = X_train['atr_pct_14'] > threshold_val
            regime_multiplier = np.where(is_extreme, 0.1, 1.0)
            sample_weights = sample_weights * regime_multiplier
            print(f"[ML Model] Extremely volatile samples (top 1% ATR > {threshold_val:.4f}) downweighted to 0.1 coefficient.")
            
        model_save_path = get_model_path(model_type, resample_minutes)
        
        if model_type.lower() == "lightgbm":
            import lightgbm as lgb
            
            # 2. Create Dataset
            train_data = lgb.Dataset(X_train, label=y_train_mapped, weight=sample_weights)
            val_data = lgb.Dataset(X_val, label=y_val_mapped, reference=train_data)
            
            # 3. Configure parameters
            params = {
                'objective': 'multiclass',
                'num_class': 3,
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'learning_rate': 0.05,
                'num_leaves': 31,
                'max_depth': 6,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'random_state': 42
            }
            
            # 4. Train model with early stopping
            print(f"[ML Model] Training LightGBM model for {num_rounds} rounds...")
            gbm = lgb.train(
                params,
                train_data,
                num_boost_round=num_rounds,
                valid_sets=[train_data, val_data],
                callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
            )
            
            # 5. Save Model
            gbm.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # 6. Evaluate on test set
            preds_prob = gbm.predict(X_test)
            preds = preds_prob.argmax(axis=1) - 1 # Map back to [-1, 0, 1]
            device = "cpu"
            
        elif model_type.lower() == "catboost":
            from catboost import CatBoostClassifier
            
            # 2. Detect GPU device check for CatBoost
            task_type = "CPU"
            try:
                test_model = CatBoostClassifier(iterations=1, task_type="GPU", random_seed=42, verbose=False)
                test_model.fit([[1.0]], [1])
                print("[ML Model] CUDA GPU detected and supported by CatBoost. Using GPU.")
                task_type = "GPU"
            except Exception as e:
                print(f"[ML Model] CatBoost CUDA GPU not available ({e}). Falling back to CPU task_type.")
                task_type = "CPU"
            
            # 3/4. Configure and train model with early stopping
            print(f"[ML Model] Training CatBoost model on {task_type} for {num_rounds} rounds...")
            model = CatBoostClassifier(
                iterations=num_rounds,
                learning_rate=0.05,
                depth=6,
                loss_function='MultiClass',
                eval_metric='MultiClass',
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
            
            # 5. Save Model
            model.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # 6. Evaluate on test set
            preds_prob = model.predict_proba(X_test)
            preds = preds_prob.argmax(axis=1) - 1
            device = task_type.lower()
            
        else: # Default: xgboost
            # 2. Detect device (GPU/CPU)
            device = get_device()
            
            # 3. Configure XGBoost parameters
            params = {
                'objective': 'multi:softprob',
                'num_class': 3,
                'eval_metric': 'mlogloss',
                'device': device,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            }
            
            # 4. Create DMatrix
            dtrain = xgb.DMatrix(X_train, label=y_train_mapped, weight=sample_weights)
            dval = xgb.DMatrix(X_val, label=y_val_mapped)
            dtest = xgb.DMatrix(X_test, label=y_test_mapped)
            
            # 5. Train model with early stopping
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
            
            # 6. Save model checkpoint
            bst.save_model(str(model_save_path))
            print(f"[ML Model] Model saved successfully to {model_save_path}")
            
            # 7. Evaluate on test set
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

def load_model(model_type: str = "xgboost", resample_minutes: Optional[int] = None) -> Optional[Any]:
    """Loads the trained ML model (XGBoost, LightGBM, or CatBoost) from disk."""
    model_path = get_model_path(model_type, resample_minutes)
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
