import pandas as pd
import numpy as np
import xgboost as xgb
from typing import Dict, Any, Tuple
from backend.services.ml.features import extract_features
from backend.services.ml.model import load_model

def evaluate_model_performance(
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame, y_val: pd.Series,
    X_test: pd.DataFrame, y_test: pd.Series,
    model: Any
) -> Dict[str, Any]:
    """
    Calculates detailed metrics (accuracy, precision, recall per class)
    for Train, Val, and Test sets to detect overfitting.
    Supports both XGBoost Booster and LightGBM Booster models.
    """
    # Detect if model is LightGBM or CatBoost
    is_lgb = False
    is_cat = False
    try:
        import lightgbm as lgb
        if isinstance(model, lgb.Booster):
            is_lgb = True
    except ImportError:
        pass
        
    try:
        from catboost import CatBoostClassifier
        if isinstance(model, CatBoostClassifier):
            is_cat = True
    except ImportError:
        pass
        
    if is_lgb:
        train_preds = model.predict(X_train).argmax(axis=1) - 1
        val_preds = model.predict(X_val).argmax(axis=1) - 1
        test_preds = model.predict(X_test).argmax(axis=1) - 1
    elif is_cat:
        train_preds = model.predict_proba(X_train).argmax(axis=1) - 1
        val_preds = model.predict_proba(X_val).argmax(axis=1) - 1
        test_preds = model.predict_proba(X_test).argmax(axis=1) - 1
    else:
        dtrain = xgb.DMatrix(X_train)
        dval = xgb.DMatrix(X_val)
        dtest = xgb.DMatrix(X_test)
        
        # Predictions
        train_preds = model.predict(dtrain).argmax(axis=1) - 1
        val_preds = model.predict(dval).argmax(axis=1) - 1
        test_preds = model.predict(dtest).argmax(axis=1) - 1
    
    from sklearn.metrics import classification_report
    
    train_report = classification_report(y_train, train_preds, output_dict=True, zero_division=0)
    val_report = classification_report(y_val, val_preds, output_dict=True, zero_division=0)
    test_report = classification_report(y_test, test_preds, output_dict=True, zero_division=0)
    
    # Overfitting Warning Check
    train_f1 = train_report["macro avg"]["f1-score"]
    val_f1 = val_report["macro avg"]["f1-score"]
    test_f1 = test_report["macro avg"]["f1-score"]
    
    overfitting_warning = False
    if train_f1 - val_f1 > 0.15:
        overfitting_warning = True
        print(f"[WARNING] Overfitting detected! Train F1: {train_f1:.2f} vs Val F1: {val_f1:.2f}")
        
    # Simple Backtest P&L Simulation on Test Set
    # Assume we take a position based on prediction: 1 (LONG), -1 (SHORT), 0 (HOLD)
    # P&L is calculated as the sum of returns over the target window
    current_pnl = 0.0
    equity_curve = [100.0] # Start with $100
    
    # Simple simulation: if prediction is UP, we buy; if DOWN, we short
    # We assume a fixed transaction cost of 0.07% (fee + slippage)
    transaction_cost = 0.07
    
    for i in range(len(test_preds)):
        pred = test_preds[i]
        actual = y_test.iloc[i]
        
        if pred == 1: # LONG
            trade_return = (actual * 0.15) - transaction_cost # Simplified return scaling
            current_pnl += trade_return
        elif pred == -1: # SHORT
            trade_return = (-actual * 0.15) - transaction_cost
            current_pnl += trade_return
            
        equity_curve.append(100.0 + current_pnl)
        
    return {
        "train": {
            "accuracy": train_report["accuracy"],
            "precision": train_report["macro avg"]["precision"],
            "recall": train_report["macro avg"]["recall"],
            "f1": train_f1
        },
        "val": {
            "accuracy": val_report["accuracy"],
            "precision": val_report["macro avg"]["precision"],
            "recall": val_report["macro avg"]["recall"],
            "f1": val_f1
        },
        "test": {
            "accuracy": test_report["accuracy"],
            "precision": test_report["macro avg"]["precision"],
            "recall": test_report["macro avg"]["recall"],
            "f1": test_f1
        },
        "overfitting_warning": overfitting_warning,
        "backtest_pnl": current_pnl,
        "equity_curve": equity_curve[-100:] # Return last 100 points for visualization
    }
 
def predict_live(df_latest: pd.DataFrame, model_type: str = "xgboost") -> Tuple[int, float]:
    """
    Generates prediction and confidence score for the latest candle.
    Returns: (prediction [-1, 0, 1], confidence [0.0 - 1.0])
    """
    model = load_model(model_type)
    if model is None:
        return 0, 0.0
        
    # Extract features for the latest candle
    features = extract_features(df_latest)
    latest_features = features.iloc[[-1]]
    
    if model_type.lower() == "lightgbm":
        probs = model.predict(latest_features)[0]
    elif model_type.lower() == "catboost":
        probs = model.predict_proba(latest_features)[0]
    else:
        dmatrix = xgb.DMatrix(latest_features)
        probs = model.predict(dmatrix)[0]
    
    pred_class_idx = probs.argmax()
    pred_class = pred_class_idx - 1 # Map [0, 1, 2] back to [-1, 0, 1]
    confidence = float(probs[pred_class_idx])
    
    return pred_class, confidence
