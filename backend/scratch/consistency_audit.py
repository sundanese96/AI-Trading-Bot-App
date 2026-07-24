"""
Cross-Asset Model Consistency Benchmark.
Runs training and evaluation on multiple assets (BTC, ETH, SOL, BNB)
to determine which model (XGBoost, LightGBM, CatBoost) is the most consistent.
"""
import sys
sys.path.insert(0, '/media/sun/DATA/sentix-ai-crypto-simulator')

import pandas as pd
import numpy as np
from pathlib import Path
from backend.services.ml.model import train_model

FEATHER_DIR = Path("/media/sun/DATA/sentix-ai-crypto-simulator/Train-data")
ASSETS = {
    "BTC": "BTCUSDT_5m.feather",
    "ETH": "ETHUSDT_5m.feather",
    "SOL": "SOLUSDT_5m.feather",
    "BNB": "BNBUSDT_5m.feather"
}

def audit_consistency():
    summary_results = []
    timeframes = [5, 15, 60, 180]
    
    for tf in timeframes:
        print(f"\n======================================== TIMEFRAME: {tf}m ========================================")
        for name, filename in ASSETS.items():
            filepath = FEATHER_DIR / filename
            if not filepath.exists():
                continue
                
            print(f"\nEvaluating {tf}m on asset: {name}")
            
            for m_type in ["xgboost", "lightgbm", "catboost"]:
                try:
                    metrics = train_model(
                        file_path=str(filepath),
                        num_rounds=100,
                        model_type=m_type,
                        resample_minutes=tf,
                        symbol=name,
                        use_binary_mode=True,
                        tp_multiplier=2.0,
                        sl_multiplier=1.0,
                        max_holding=15
                    )
                    
                    acc = metrics.get("test", {}).get("accuracy", 0.0)
                    f1 = metrics.get("test", {}).get("f1", 0.0)
                    pnl = metrics.get("backtest_pnl", 0.0)
                    
                    summary_results.append({
                        "Timeframe": tf,
                        "Asset": name,
                        "Model": m_type.upper(),
                        "Accuracy": acc,
                        "F1": f1,
                        "PnL": pnl
                    })
                    print(f"  [{m_type.upper()}] Acc: {acc:.4f} | F1: {f1:.4f} | PnL: {pnl:.2f}%")
                except Exception as e:
                    print(f"  [{m_type.upper()}] Error: {e}")
                
    # Compile Summary Dataframe
    df_res = pd.DataFrame(summary_results)
    print("\n" + "="*80)
    print("                      CROSS-ASSET CONSISTENCY REPORT (ALL TIMEFRAMES)")
    print("="*80)
    print(df_res.to_string(index=False))
    
    print("\n" + "="*80)
    print("                      AVERAGE MODEL PERFORMANCE BY TIMEFRAME")
    print("="*80)
    grouped = df_res.groupby(["Timeframe", "Model"]).agg({
        "Accuracy": ["mean", "std"],
        "F1": ["mean", "std"],
        "PnL": ["mean"]
    })
    print(grouped)
    
    print("\n" + "="*80)
    print("                      GLOBAL AVERAGE MODEL PERFORMANCE")
    print("="*80)
    global_grouped = df_res.groupby("Model").agg({
        "Accuracy": ["mean", "std"],
        "F1": ["mean", "std"],
        "PnL": ["mean"]
    })
    print(global_grouped)
    print("="*80)

if __name__ == "__main__":
    audit_consistency()
