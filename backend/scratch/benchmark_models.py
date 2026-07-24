import sys
import pandas as pd
from pathlib import Path
from backend.services.ml.model import load_model
from backend.services.ml.data_prep import prepare_training_data
from backend.services.ml.evaluator import evaluate_model_performance

FEATHER_PATH = Path("/media/sun/DATA/sentix-ai-crypto-simulator/Train-data/BTCUSDT_5m.feather")
if not FEATHER_PATH.exists():
    FEATHER_PATH = Path("/media/sun/DATA/sentix-ai-crypto-simulator/backend/btc_1m_mock.feather")

print(f"Loading evaluation dataset from: {FEATHER_PATH}")

try:
    timeframes = [5, 15, 60]
    models = ["xgboost", "lightgbm", "catboost"]
    
    print("\n" + "="*70)
    print(" SENSITIVITY BENCHMARK REPORT: ML MODELS CROSS-TIMEFRAME ")
    print("="*70)
    
    overall_best = []
    
    for tf in timeframes:
        # Prepare historical validation sets for this timeframe resample rate
        _, _, train, val, test = prepare_training_data(
            str(FEATHER_PATH), target_window=15, threshold_pct=0.15, resample_minutes=tf
        )
        X_train, y_train = train
        X_val, y_val = val
        X_test, y_test = test
        
        print(f"\nTimeframe: {tf}m | Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
        print("-" * 50)
        
        tf_results = {}
        for m_type in models:
            model = load_model(m_type, resample_minutes=tf, symbol="BTC")
            if model is None:
                print(f"[-] {m_type.upper()}: No model file found for {tf}m.")
                continue
                
            metrics = evaluate_model_performance(X_train, y_train, X_val, y_val, X_test, y_test, model)
            tf_results[m_type] = metrics
            
            print(f"  📈 {m_type.upper()}:")
            print(f"    ├─ Test Accuracy : {metrics['test']['accuracy']:.4f}")
            print(f"    ├─ Test F1-Score : {metrics['test']['f1']:.4f}")
            print(f"    ├─ Backtest P&L  : {metrics['backtest_pnl']:.2f}%")
            print(f"    └─ Overfitting?  : {'⚠️ YES' if metrics['overfitting_warning'] else '✅ NO'}")
            
        if tf_results:
            best_tf = max(tf_results.keys(), key=lambda k: tf_results[k]["test"]["accuracy"])
            overall_best.append((tf, best_tf, tf_results[best_tf]["test"]["accuracy"]))
            print(f"  🏆 Best for {tf}m: {best_tf.upper()} ({tf_results[best_tf]['test']['accuracy']:.4f} Acc)")
            
    if overall_best:
        print("\n" + "="*70)
        best_overall_run = max(overall_best, key=lambda x: x[2])
        print(f"🏆 BEST OVERALL CONFIG: {best_overall_run[1].upper()} on {best_overall_run[0]}m timeframe ({best_overall_run[2]:.4f} Acc)")
        print("="*70 + "\n")
    else:
        print("\n[-] Error: No trained models available for benchmark. Train models first in the UI.")
        
except Exception as e:
    print(f"Evaluation error: {e}", file=sys.stderr)
