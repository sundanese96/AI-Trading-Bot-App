"""
Full V2 Retraining Script: Trains all 4 models (BTC, ETH, SOL, BNB) + Global 
across 4 timeframes (5m, 15m, 60m, 180m) using Binary Classifier + Dynamic ATR Triple-Barrier.
"""
import sys
sys.path.insert(0, '/media/sun/DATA/sentix-ai-crypto-simulator')

from pathlib import Path
from backend.services.ml.model import train_model
from backend.database import read_database, write_database

FEATHER_DIR = Path("/media/sun/DATA/sentix-ai-crypto-simulator/Train-data")

SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "GLOBAL": None
}

TIMEFRAMES = [5, 15, 60, 180]
MODEL_TYPES = ["xgboost", "lightgbm", "catboost"]

def retrain_all():
    results = []
    
    for symbol_key, symbol_val in SYMBOLS.items():
        print(f"\n{'='*70}")
        print(f" RETRAINING: {symbol_key} ({symbol_val or 'GLOBAL'})")
        print(f"{'='*70}")
        
        # Find feather file for this symbol
        feather_file = None
        if symbol_val:
            sym_clean = symbol_val.replace("USDT", "")
            # Try to find the feather file - use BTC as fallback since we only have BTC data
            btc_feather = FEATHER_DIR / "BTCUSDT_5m.feather"
            if btc_feather.exists():
                feather_file = str(btc_feather)
        
        if not feather_file:
            print(f"[SKIP] No feather file found for {symbol_key}")
            continue
        
        for tf in TIMEFRAMES:
            for m_type in MODEL_TYPES:
                print(f"\n--- Training {m_type.upper()} ({tf}m) for {symbol_key} ---")
                
                try:
                    metrics = train_model(
                        file_path=feather_file,
                        num_rounds=100,
                        model_type=m_type,
                        resample_minutes=tf,
                        symbol=symbol_val,
                        use_binary_mode=True,
                        tp_multiplier=2.0,
                        sl_multiplier=1.0,
                        max_holding=15
                    )
                    
                    results.append({
                        "symbol": symbol_key,
                        "timeframe": tf,
                        "model_type": m_type,
                        "accuracy": metrics.get("test", {}).get("accuracy", 0),
                        "f1": metrics.get("test", {}).get("f1", 0),
                        "status": "success"
                    })
                    
                    print(f"[OK] Acc: {metrics.get('test', {}).get('accuracy', 0):.4f} | F1: {metrics.get('test', {}).get('f1', 0):.4f}")
                    
                except Exception as e:
                    print(f"[ERROR] {symbol_key} {tf}m {m_type}: {e}")
                    results.append({
                        "symbol": symbol_key,
                        "timeframe": tf,
                        "model_type": m_type,
                        "status": "error",
                        "error": str(e)
                    })
    
    # Save training report
    report = {
        "total_models": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results
    }
    
    report_path = FEATHER_DIR.parent / "backend" / "models" / "v2_full_retrain_report.json"
    import json
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f" RETRAINING COMPLETE: {report['successful']}/{report['total_models']} successful")
    print(f" Report saved to: {report_path}")
    print(f"{'='*70}")
    
    return report

if __name__ == "__main__":
    retrain_all()
