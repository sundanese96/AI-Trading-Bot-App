# backend/services/indicators.py

def calculate_sma(prices, period):
    smas = [None] * len(prices)
    for i in range(period - 1, len(prices)):
        smas[i] = sum(prices[i - period + 1 : i + 1]) / period
    return smas

def calculate_ema(prices, period):
    emas = [None] * len(prices)
    if len(prices) < period:
        return emas
    # Seed with SMA
    emas[period - 1] = sum(prices[:period]) / period
    multiplier = 2 / (period + 1)
    for i in range(period, len(prices)):
        emas[i] = (prices[i] - emas[i - 1]) * multiplier + emas[i - 1]
    return emas

def calculate_rsi(prices, period=14):
    rsi = [None] * len(prices)
    if len(prices) <= period:
        return rsi
    
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi[period] = 100
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))
        
    for i in range(period + 1, len(prices)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices):
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd_line = [None] * len(prices)
    for i in range(len(prices)):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line[i] = ema12[i] - ema26[i]
            
    macd_signal = [None] * len(prices)
    start_idx = -1
    for i in range(len(macd_line)):
        if macd_line[i] is not None:
            start_idx = i
            break
            
    if start_idx != -1 and len(macd_line) - start_idx >= 9:
        sum_macd = 0.0
        for i in range(start_idx, start_idx + 9):
            sum_macd += macd_line[i]
        macd_signal[start_idx + 8] = sum_macd / 9
        
        multiplier = 2 / (9 + 1)
        for i in range(start_idx + 9, len(macd_line)):
            if macd_line[i] is not None and macd_signal[i - 1] is not None:
                macd_signal[i] = (macd_line[i] - macd_signal[i - 1]) * multiplier + macd_signal[i - 1]
                
    macd_hist = [None] * len(prices)
    for i in range(len(prices)):
        if macd_line[i] is not None and macd_signal[i] is not None:
            macd_hist[i] = macd_line[i] - macd_signal[i]
            
    return macd_line, macd_signal, macd_hist

def calculate_bollinger_bands(prices, period=20, num_std=2):
    middle = [None] * len(prices)
    upper = [None] * len(prices)
    lower = [None] * len(prices)
    
    for i in range(period - 1, len(prices)):
        slice_prices = prices[i - period + 1 : i + 1]
        mean = sum(slice_prices) / period
        variance = sum((x - mean) ** 2 for x in slice_prices) / period
        std = max(0.0, variance) ** 0.5
        middle[i] = mean
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
        
    return middle, upper, lower
