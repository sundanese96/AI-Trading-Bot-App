import numpy as np
import pandas as pd
from typing import Dict, Any, List

def detect_smc_structures(df: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
    """
    SMC (Smart Money Concepts) Structural Analysis.
    Detects BOS (Break of Structure), CHoCH (Change of Character), 
    and FVG (Fair Value Gaps) from candle histories.
    """
    if len(df) < 15:
        return {
            "trend": "Sideways",
            "bos_detected": False,
            "choch_detected": False,
            "fvg_zones": [],
            "order_blocks": []
        }
        
    df = df.copy()
    
    # 1. Identify local swing highs and swing lows (pivots)
    df['swing_high'] = False
    df['swing_low'] = False
    
    for i in range(window, len(df) - window):
        chunk_high = df['high'].iloc[i - window : i + window + 1]
        chunk_low = df['low'].iloc[i - window : i + window + 1]
        
        if df['high'].iloc[i] == chunk_high.max():
            df.loc[df.index[i], 'swing_high'] = True
        if df['low'].iloc[i] == chunk_low.min():
            df.loc[df.index[i], 'swing_low'] = True
            
    # 2. Detect Fair Value Gaps (FVG) - 3 candle imbalance
    # Bullish FVG: Low of candle 3 > High of candle 1
    # Bearish FVG: High of candle 3 < Low of candle 1
    fvg_zones = []
    for i in range(2, len(df)):
        c1_high = float(df['high'].iloc[i-2])
        c1_low = float(df['low'].iloc[i-2])
        c3_high = float(df['high'].iloc[i])
        c3_low = float(df['low'].iloc[i])
        
        # Bullish FVG
        if c3_low > c1_high:
            fvg_gap = c3_low - c1_high
            fvg_zones.append({
                "type": "BULLISH",
                "top": c3_low,
                "bottom": c1_high,
                "gap_size": fvg_gap,
                "index": i-1
            })
        # Bearish FVG
        elif c3_high < c1_low:
            fvg_gap = c1_low - c3_high
            fvg_zones.append({
                "type": "BEARISH",
                "top": c1_low,
                "bottom": c3_high,
                "gap_size": fvg_gap,
                "index": i-1
            })
            
    # 3. Detect CHoCH and BOS based on price breakouts of swing levels
    bos = False
    choch = False
    trend = "Sideways"
    
    # Extract last verified swing points
    high_pivots = df[df['swing_high'] == True]['high'].tolist()
    low_pivots = df[df['swing_low'] == True]['low'].tolist()
    
    current_close = float(df['close'].iloc[-1])
    
    if len(high_pivots) >= 2 and len(low_pivots) >= 2:
        last_high = high_pivots[-1]
        prev_high = high_pivots[-2]
        last_low = low_pivots[-1]
        prev_low = low_pivots[-2]
        
        # Break of Structure (BOS): continuation of direction
        if current_close > last_high:
            bos = True
            trend = "Bullish"
        elif current_close < last_low:
            bos = True
            trend = "Bearish"
            
        # Change of Character (CHoCH): break of counter-trend pivot
        # If previous trend was bearish (making lower highs) and we break above the last swing high
        if current_close > last_high and last_high < prev_high:
            choch = True
            trend = "Bullish (Reversal)"
        # If previous trend was bullish (making higher lows) and we break below the last swing low
        elif current_close < last_low and last_low > prev_low:
            choch = True
            trend = "Bearish (Reversal)"
            
    # Return detected parameters
    return {
        "trend": trend,
        "bos_detected": bos,
        "choch_detected": choch,
        "fvg_zones": fvg_zones[-3:], # Keep last 3 gaps for target range filling
        "last_high_pivot": high_pivots[-1] if high_pivots else None,
        "last_low_pivot": low_pivots[-1] if low_pivots else None
    }
