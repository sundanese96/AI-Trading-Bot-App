import sys
import pandas as pd
from pathlib import Path
from backend.services.ml.model import load_model, get_model_path
from backend.services.ml.data_prep import prepare_training_data
from backend.services.ml.evaluator import evaluate_model_performance

# We test performance using the downloaded BTC dataset at 5m resample rate
FEATHER_PATH = Path("/media/sun/DATA/sentix-ai-crypto-simulator/Train-data/BTCUSDT_5m.feather")
if not FEATHER_PATH.exists():
    FEATHER_PATH = Path("/media/sun/DATA/sentix-ai-crypto-simulator/backend/btc_1m_mock.feather")

print(f"Loading evaluation dataset from: {FEATHER_PATH}")

try:
    # Prepare historical validation sets
    _, _, train, val, test = prepare_training_data(
        str(FEATHER_PATH), target_window=15, threshold_pct=0.15, resample_minutes=5
    )
    X_train, y_train = train
    X_val, y_val = val
    X_test, y_test = test
    
    print(f"Data ready. Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
    
    models = ["xgboost", "lightgbm", "catboost"]
    results = {}
    
    print("\n" + "="*50)
    print(" SENSITIVITY BENCHMARK REPORT: ML MODELS ")
    print("="*50)
    
    for m_type in models:
        model = load_model(m_type, resample_minutes=5, symbol="BTC")
        if model is None:
            print(f"[-] {m_type.upper()}: No model file found on disk.")
            continue
            
        metrics = evaluate_model_performance(X_train, y_train, X_val, y_val, X_test, y_test, model)
        results[m_type] = metrics
        
        print(f"\n📈 MODEL: {m_type.upper()}")
        print(f"  ├─ Test Accuracy : {metrics['test']['accuracy']:.4f}")
        print(f"  ├─ Test F1-Score : {metrics['test']['f1']:.4f}")
        print(f"  ├─ Backtest P&L  : {metrics['backtest_pnl']:.2f}%")
        print(f"  └─ Overfitting?  : {'⚠️ YES (Warning)' if metrics['overfitting_warning'] else '✅ NO'}")
        
    if results:
        best_model = max(results.keys(), key=lambda k: results[k]["test"]["accuracy"])
        print("\n" + "="*50)
        print(f"🏆 BEST PERFORMANCE MODEL: {best_model.upper()}")
        print("="*50 + "\n")
    else:
        print("\n[-] Error: No trained models available for benchmark. Train models first in the UI.")
        
except Exception as e:
    print(f"Evaluation error: {e}", file=sys.stderr)
