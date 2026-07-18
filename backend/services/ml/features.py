import os
import pandas as pd
import numpy as np
from backend.config import VERIFY_SSL

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates the Relative Strength Index (RSI) for a given DataFrame."""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """Calculates the MACD line, Signal line, and Histogram."""
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> tuple:
    """Calculates Bollinger Bands and returns distance percentages from bands."""
    sma = df['close'].rolling(window=period).mean()
    rstd = df['close'].rolling(window=period).std()
    upper_band = sma + std_dev * rstd
    lower_band = sma - std_dev * rstd
    
    # Distance percentages
    pct_from_upper = (upper_band - df['close']) / (df['close'] + 1e-9) * 100
    pct_from_lower = (df['close'] - lower_band) / (df['close'] + 1e-9) * 100
    return upper_band, lower_band, pct_from_upper, pct_from_lower

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates the Average True Range (ATR) normalized by close price."""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr / (df['close'] + 1e-9) * 100

def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculates Chaikin Money Flow (CMF)."""
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'] + 1e-9)
    mf_volume = mf_multiplier * df['volume']
    return mf_volume.rolling(window=period).sum() / (df['volume'].rolling(window=period).sum() + 1e-9)

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates the Average Directional Index (ADX) without external dependencies."""
    upmove = df['high'].diff()
    downmove = df['low'].diff()
    
    plus_dm = np.where((upmove > downmove) & (upmove > 0), upmove, 0.0)
    minus_dm = np.where((downmove > upmove) & (downmove > 0), downmove, 0.0)
    
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period, min_periods=1).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window=period, min_periods=1).mean() / (atr + 1e-9)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window=period, min_periods=1).mean() / (atr + 1e-9)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    adx = dx.rolling(window=period, min_periods=1).mean().fillna(0.0)
    return pd.Series(adx, index=df.index)

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts technical indicators as features from raw OHLCV data.
    Now includes funding rates, cross-asset correlation features, and market regime context.
    """
    features = pd.DataFrame(index=df.index)
    
    # Trend
    features['rsi_14'] = calculate_rsi(df, 14)
    macd_line, signal_line, macd_hist = calculate_macd(df, 12, 26, 9)
    features['macd_line'] = macd_line
    features['macd_signal'] = signal_line
    features['macd_hist'] = macd_hist
    
    # Volatility
    _, _, pct_upper, pct_lower = calculate_bollinger_bands(df, 20, 2.0)
    features['bb_pct_upper'] = pct_upper
    features['bb_pct_lower'] = pct_lower
    features['atr_pct_14'] = calculate_atr(df, 14)
    
    # Market Volatility & Trend Regimes
    features['volatility_regime'] = features['atr_pct_14'].rolling(window=8640, min_periods=1).rank(pct=True).fillna(0.5)
    ema200 = df['close'].ewm(span=200, adjust=False).mean()
    features['trend_regime_slope'] = (ema200.diff(periods=10) / (df['close'] + 1e-9) * 100).fillna(0.0)
    features['adx_14'] = calculate_adx(df, 14)
    
    # Volume
    features['cmf_20'] = calculate_cmf(df, 20)
    volume_sma = df['volume'].rolling(window=20).mean()
    features['volume_sma_ratio'] = df['volume'] / (volume_sma + 1e-9)
    
    # --- Funding Rates & Cross-Asset Features ---
    # Ensure there is a date column to align on
    date_col = 'date' if 'date' in df.columns else ('timestamp' if 'timestamp' in df.columns else None)
    
    if date_col:
        # Align index to datetime for easier reindexing
        original_idx = df.index
        times = pd.to_datetime(df[date_col])
        if hasattr(times, "dt"):
            times = times.dt.tz_localize(None)
        else:
            times = times.tz_localize(None)
        
        # Load auxiliary close price datasets
        data_dir = "Train-data"
        eth_path = f"{data_dir}/ETHUSDT_5m.feather"
        sol_path = f"{data_dir}/SOLUSDT_5m.feather"
        bnb_path = f"{data_dir}/BNBUSDT_5m.feather"
        
        btc_funding_path = f"{data_dir}/BTCUSDT_funding_rates.feather"
        eth_funding_path = f"{data_dir}/ETHUSDT_funding_rates.feather"
        sol_funding_path = f"{data_dir}/SOLUSDT_funding_rates.feather"
        bnb_funding_path = f"{data_dir}/BNBUSDT_funding_rates.feather"
        
        # Default fallback series if file not found (e.g. during dry-run tests)
        eth_close = pd.Series(df['close'].values, index=times)
        sol_close = pd.Series(df['close'].values, index=times)
        bnb_close = pd.Series(df['close'].values, index=times)
        
        btc_funding = pd.Series(0.0, index=times)
        eth_funding = pd.Series(0.0, index=times)
        sol_funding = pd.Series(0.0, index=times)
        bnb_funding = pd.Series(0.0, index=times)

        # 1. Determine if we are in LIVE mode or BACKTEST mode
        # If the number of samples is small (e.g., < 500) and times contains timestamps after July 9th, 2026 (or feather files are missing), we switch to live mode.
        max_feather_time = pd.to_datetime('2026-07-09 00:00:00')
        max_time = times.max()
        if hasattr(max_time, "tzinfo") and max_time.tzinfo is not None:
            max_time = max_time.tz_localize(None)
            
        is_live_mode = (
            len(times) < 500 and (
                not os.path.exists(eth_path) or
                not os.path.exists(sol_path) or
                not os.path.exists(bnb_path) or
                max_time > max_feather_time
            )
        )
        
        if is_live_mode:
            # --- LIVE MODE: Fetch data dynamically from Binance Futures public API ---
            # Determine time interval from times diff
            if len(times) >= 2:
                diff_min = int((times.iloc[-1] - times.iloc[-2]).total_seconds() / 60)
                if diff_min == 1:
                    interval = "1m"
                elif diff_min == 5:
                    interval = "5m"
                elif diff_min == 15:
                    interval = "15m"
                elif diff_min == 60:
                    interval = "1h"
                else:
                    interval = f"{diff_min}m"
            else:
                interval = "5m"
                
            query_end_ms = int(times.iloc[-1].timestamp() * 1000)
            
            import httpx
            def fetch_asset_live(symbol: str, end_time_ms: int, limit: int, tf: str) -> pd.Series:
                # FIX 1: Subtract 1ms to prevent future candle leakage
                query_end = end_time_ms - 1
                url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={tf}&limit={limit}&endTime={query_end}"
                try:
                    resp = httpx.get(url, verify=VERIFY_SSL, timeout=10.0)
                    if resp.status_code == 200:
                        klines = resp.json()
                        close_prices = [float(k[4]) for k in klines]
                        open_times = [pd.to_datetime(k[0], unit='ms').tz_localize(None) for k in klines]
                        return pd.Series(close_prices, index=open_times)
                except Exception as ex:
                    print(f"[Features Live Fetch] Warning: Error fetching {symbol} live candles: {ex}")
                return None
                
            def fetch_funding_live(symbol: str, end_time_ms: int, limit: int = 15) -> pd.DataFrame:
                url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit={limit}&endTime={end_time_ms}"
                try:
                    resp = httpx.get(url, verify=VERIFY_SSL, timeout=10.0)
                    if resp.status_code == 200:
                        rates = resp.json()
                        dates = [pd.to_datetime(r['fundingTime'], unit='ms').tz_localize(None) for r in rates]
                        vals = [float(r['fundingRate']) for r in rates]
                        return pd.DataFrame({'fundingRate': vals}, index=dates)
                except Exception as ex:
                    print(f"[Features Live Fetch] Warning: Error fetching {symbol} live funding: {ex}")
                return None

            print(f"[Features] Running in LIVE mode at timestamp {times.max()}. Fetching cross-asset details dynamically...")
            
            # Fetch ETHUSDT close prices
            eth_live = fetch_asset_live("ETHUSDT", query_end_ms, len(df), interval)
            if eth_live is not None and not eth_live.empty:
                eth_close = eth_live.reindex(times, method='ffill').bfill()
            
            # Fetch SOLUSDT close prices
            sol_live = fetch_asset_live("SOLUSDT", query_end_ms, len(df), interval)
            if sol_live is not None and not sol_live.empty:
                sol_close = sol_live.reindex(times, method='ffill').bfill()
                
            # Fetch BNBUSDT close prices
            bnb_live = fetch_asset_live("BNBUSDT", query_end_ms, len(df), interval)
            if bnb_live is not None and not bnb_live.empty:
                bnb_close = bnb_live.reindex(times, method='ffill').bfill()
                
            # Fetch funding rates
            btc_fun_live = fetch_funding_live("BTCUSDT", query_end_ms)
            if btc_fun_live is not None and not btc_fun_live.empty:
                btc_funding = btc_fun_live['fundingRate'].reindex(times, method='ffill').bfill()
                
            eth_fun_live = fetch_funding_live("ETHUSDT", query_end_ms)
            if eth_fun_live is not None and not eth_fun_live.empty:
                eth_funding = eth_fun_live['fundingRate'].reindex(times, method='ffill').bfill()
                
            sol_fun_live = fetch_funding_live("SOLUSDT", query_end_ms)
            if sol_fun_live is not None and not sol_fun_live.empty:
                sol_funding = sol_fun_live['fundingRate'].reindex(times, method='ffill').bfill()
                
            bnb_fun_live = fetch_funding_live("BNBUSDT", query_end_ms)
            if bnb_fun_live is not None and not bnb_fun_live.empty:
                bnb_funding = bnb_fun_live['fundingRate'].reindex(times, method='ffill').bfill()

        else:
            # --- BACKTEST/DRY-RUN MODE: Use offline feather datasets ---
            try:
                # 1. Aligned ETH Close
                if os.path.exists(eth_path):
                    eth_df = pd.read_feather(eth_path)
                    eth_df['date'] = pd.to_datetime(eth_df['date'])
                    eth_df = eth_df.drop_duplicates(subset=['date']).set_index('date')
                    eth_close = eth_df['close'].reindex(times, method='ffill').bfill()
                
                # 2. Aligned SOL Close
                if os.path.exists(sol_path):
                    sol_df = pd.read_feather(sol_path)
                    sol_df['date'] = pd.to_datetime(sol_df['date'])
                    sol_df = sol_df.drop_duplicates(subset=['date']).set_index('date')
                    sol_close = sol_df['close'].reindex(times, method='ffill').bfill()
                    
                # 3. Aligned BNB Close
                if os.path.exists(bnb_path):
                    bnb_df = pd.read_feather(bnb_path)
                    bnb_df['date'] = pd.to_datetime(bnb_df['date'])
                    bnb_df = bnb_df.drop_duplicates(subset=['date']).set_index('date')
                    bnb_close = bnb_df['close'].reindex(times, method='ffill').bfill()
                    
                # 4. Aligned BTC Funding Rate
                if os.path.exists(btc_funding_path):
                    btc_fun_df = pd.read_feather(btc_funding_path)
                    btc_fun_df['date'] = pd.to_datetime(btc_fun_df['date'])
                    btc_fun_df = btc_fun_df.drop_duplicates(subset=['date']).set_index('date')
                    btc_funding = btc_fun_df['fundingRate'].reindex(times, method='ffill').bfill()
                
                # 5. Aligned ETH Funding Rate
                if os.path.exists(eth_funding_path):
                    eth_fun_df = pd.read_feather(eth_funding_path)
                    eth_fun_df['date'] = pd.to_datetime(eth_fun_df['date'])
                    eth_fun_df = eth_fun_df.drop_duplicates(subset=['date']).set_index('date')
                    eth_funding = eth_fun_df['fundingRate'].reindex(times, method='ffill').bfill()
                    
                # 6. Aligned SOL Funding Rate
                if os.path.exists(sol_funding_path):
                    sol_fun_df = pd.read_feather(sol_funding_path)
                    sol_fun_df['date'] = pd.to_datetime(sol_fun_df['date'])
                    sol_fun_df = sol_fun_df.drop_duplicates(subset=['date']).set_index('date')
                    sol_funding = sol_fun_df['fundingRate'].reindex(times, method='ffill').bfill()
                    
                # 7. Aligned BNB Funding Rate
                if os.path.exists(bnb_funding_path):
                    bnb_fun_df = pd.read_feather(bnb_funding_path)
                    bnb_fun_df['date'] = pd.to_datetime(bnb_fun_df['date'])
                    bnb_fun_df = bnb_fun_df.drop_duplicates(subset=['date']).set_index('date')
                    bnb_funding = bnb_fun_df['fundingRate'].reindex(times, method='ffill').bfill()
                    
            except Exception as e:
                print(f"[Features] Warning: Error aligning cross-asset features: {e}. Falling back to default indicators.")
                
        # --- Flatline Validation Guards ---
        for asset_name, close_series in [("ETH", eth_close), ("SOL", sol_close), ("BNB", bnb_close)]:
            pct = close_series.pct_change().fillna(0.0)
            if len(pct) >= 10:
                last_10 = pct.iloc[-10:]
                if (last_10 == 0.0).all():
                    print(f"[WARNING] Feature engineering flatline alert: {asset_name} close price has been constant 0.0 returns for the last 10 candles. Data leakage or feed issue suspected.")
            
        # Write features with original numeric index
        close_indexed = pd.Series(df['close'].values, index=times)
        
        # Stationary Rolling Return Correlations (Percentage Changes)
        ret_btc = close_indexed.pct_change(1).fillna(0.0)
        ret_eth = eth_close.pct_change(1).fillna(0.0)
        ret_sol = sol_close.pct_change(1).fillna(0.0)
        
        corr_eth_20 = ret_btc.rolling(window=20).corr(ret_eth)
        corr_sol_20 = ret_btc.rolling(window=20).corr(ret_sol)
        corr_eth_100 = ret_btc.rolling(window=100).corr(ret_eth)
        corr_sol_100 = ret_btc.rolling(window=100).corr(ret_sol)
        
        features['corr_btc_eth_20'] = corr_eth_20.fillna(0.0).values
        features['corr_btc_sol_20'] = corr_sol_20.fillna(0.0).values
        features['corr_btc_eth_100'] = corr_eth_100.fillna(0.0).values
        features['corr_btc_sol_100'] = corr_sol_100.fillna(0.0).values
        
        # Cointegration/Log-Spread Z-Scores
        log_spread_eth = np.log(close_indexed + 1e-9) - np.log(eth_close + 1e-9)
        z_spread_eth = (log_spread_eth - log_spread_eth.rolling(100).mean()) / (log_spread_eth.rolling(100).std() + 1e-9)
        
        log_spread_sol = np.log(close_indexed + 1e-9) - np.log(sol_close + 1e-9)
        z_spread_sol = (log_spread_sol - log_spread_sol.rolling(100).mean()) / (log_spread_sol.rolling(100).std() + 1e-9)
        
        log_spread_bnb = np.log(close_indexed + 1e-9) - np.log(bnb_close + 1e-9)
        z_spread_bnb = (log_spread_bnb - log_spread_bnb.rolling(100).mean()) / (log_spread_bnb.rolling(100).std() + 1e-9)
        
        features['ratio_btc_eth_norm'] = z_spread_eth.fillna(0.0).values
        features['ratio_btc_sol_norm'] = z_spread_sol.fillna(0.0).values
        features['ratio_btc_bnb_norm'] = z_spread_bnb.fillna(0.0).values
        
        # Funding rate (forward-filled)
        features['btc_funding_rate'] = btc_funding.fillna(0.0).values
        
        # Funding Rate Momentum (differential changes)
        features['funding_mom_1'] = btc_funding.diff(1).fillna(0.0).values
        features['funding_mom_3'] = btc_funding.diff(3).fillna(0.0).values
        
        # Funding Spreads (Alt Speculative Premium relative to BTC)
        features['funding_spread_eth'] = (btc_funding - eth_funding).fillna(0.0).values
        features['funding_spread_sol'] = (btc_funding - sol_funding).fillna(0.0).values
        features['funding_spread_bnb'] = (btc_funding - bnb_funding).fillna(0.0).values
        
    return features