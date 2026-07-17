import pandas as pd
import numpy as np

def generate_mock_feather_data(file_path: str):
    """Generates 10,000 candles of mock trade data and saves to feather format."""
    print(f"[Mock Data] Generating mock feather data at {file_path}...")
    np.random.seed(42)
    dates = pd.date_range(start="2026-01-01", periods=10000, freq="min")
    
    close = 60000.0
    closes = []
    highs = []
    lows = []
    opens = []
    volumes = []
    
    for _ in range(10000):
        change = np.random.normal(0, 50.0)
        new_close = close + change
        new_open = close
        new_high = max(new_open, new_close) + abs(np.random.normal(0, 10.0))
        new_low = min(new_open, new_close) - abs(np.random.normal(0, 10.0))
        new_volume = np.random.exponential(1.5)
        
        opens.append(new_open)
        closes.append(new_close)
        highs.append(new_high)
        lows.append(new_low)
        volumes.append(new_volume)
        close = new_close
        
    df = pd.DataFrame({
        "date": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })
    
    df.to_feather(file_path)
    print(f"[Mock Data] Mock data generated ({len(df)} rows) and saved successfully.")
