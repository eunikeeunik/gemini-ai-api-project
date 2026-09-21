"""
EquityLens AI - Technical Analysis Module (Fase 3 & 8)
Computes all key technical indicators algorithmically using pandas and numpy.
Gemini is NEVER allowed to guess or calculate technical metrics.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()

def compute_bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    bandwidth = ((upper - lower) / sma) * 100.0
    return upper, sma, lower, bandwidth

def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def find_support_resistance(df: pd.DataFrame, window: int = 15) -> Dict[str, List[float]]:
    """Identifies swing highs (resistance) and swing lows (support)"""
    highs = df["High"].rolling(window=window, center=True).max()
    lows = df["Low"].rolling(window=window, center=True).min()
    
    res_candidates = df[df["High"] == highs]["High"].dropna().tolist()
    sup_candidates = df[df["Low"] == lows]["Low"].dropna().tolist()
    
    current_price = float(df["Close"].iloc[-1])
    
    supports = sorted([float(p) for p in set(sup_candidates) if p < current_price * 0.995], reverse=True)[:3]
    resistances = sorted([float(p) for p in set(res_candidates) if p > current_price * 1.005])[:3]
    
    return {
        "support": supports,
        "resistance": resistances
    }

def calculate_technicals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates all indicators and outputs comprehensive technical dict"""
    if len(df) < 30:
        return {"error": "Data histori tidak mencukupi untuk kalkulasi teknikal (minimal 30 bar)"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]
    current_price = float(close.iloc[-1])

    # Moving Averages
    sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else current_price
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else current_price
    sma100 = float(close.rolling(100).mean().iloc[-1]) if len(close) >= 100 else current_price
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else current_price
    ema12 = float(close.ewm(span=12, adjust=False).mean().iloc[-1])
    ema26 = float(close.ewm(span=26, adjust=False).mean().iloc[-1])

    # RSI
    rsi_series = compute_rsi(close, 14)
    rsi14 = float(rsi_series.iloc[-1])

    # MACD
    macd_line, sig_line, macd_hist = compute_macd(close, 12, 26, 9)
    cur_macd = float(macd_line.iloc[-1])
    cur_sig = float(sig_line.iloc[-1])
    cur_hist = float(macd_hist.iloc[-1])

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower, bb_width = compute_bollinger_bands(close, 20, 2.0)
    cur_bb_upper = float(bb_upper.iloc[-1])
    cur_bb_mid = float(bb_mid.iloc[-1])
    cur_bb_lower = float(bb_lower.iloc[-1])
    cur_bb_width = float(bb_width.iloc[-1])

    # ATR
    atr_series = compute_atr(high, low, close, 14)
    cur_atr = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else current_price * 0.02

    # Squeeze detection: bandwidth lower than 20-day bandwidth average
    is_squeeze = cur_bb_width < float(bb_width.rolling(20).mean().iloc[-1])

    # Volume average
    vol_sma20 = float(vol.rolling(20).mean().iloc[-1])
    vol_ratio = float(vol.iloc[-1] / vol_sma20) if vol_sma20 > 0 else 1.0

    # 52-week High / Low
    year_df = df.tail(252)
    high_52w = float(year_df["High"].max())
    low_52w = float(year_df["Low"].min())
    pct_from_52w_high = ((current_price / high_52w) - 1.0) * 100.0

    # S/R levels
    levels = find_support_resistance(df)

    # Regime Determination
    if current_price > sma50 and sma50 >= sma200:
        regime = "uptrend"
        trend_score = 0.5
    elif current_price < sma50 and sma50 <= sma200:
        regime = "downtrend"
        trend_score = -0.5
    else:
        regime = "sideways"
        trend_score = 0.0

    # Momentum score
    momentum_score = 0.0
    if rsi14 > 55 and cur_hist > 0:
        momentum_score += 0.3
    elif rsi14 < 45 and cur_hist < 0:
        momentum_score -= 0.3

    total_technical_score = max(-1.0, min(1.0, trend_score + momentum_score))

    return {
        "score": round(total_technical_score, 2),
        "regime": regime,
        "current_price": round(current_price, 2),
        "moving_averages": {
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "sma100": round(sma100, 2),
            "sma200": round(sma200, 2),
            "ema12": round(ema12, 2),
            "ema26": round(ema26, 2),
        },
        "rsi": {
            "value": round(rsi14, 2),
            "status": "Overbought" if rsi14 >= 70 else "Oversold" if rsi14 <= 30 else "Neutral"
        },
        "macd": {
            "line": round(cur_macd, 2),
            "signal": round(cur_sig, 2),
            "histogram": round(cur_hist, 2),
            "status": "Bullish Crossover" if cur_hist > 0 and macd_hist.iloc[-2] <= 0 else "Bearish Crossover" if cur_hist < 0 and macd_hist.iloc[-2] >= 0 else "Positive" if cur_hist > 0 else "Negative"
        },
        "bollinger": {
            "upper": round(cur_bb_upper, 2),
            "middle": round(cur_bb_mid, 2),
            "lower": round(cur_bb_lower, 2),
            "bandwidth_pct": round(cur_bb_width, 2),
            "squeeze": is_squeeze
        },
        "atr14": round(cur_atr, 2),
        "volume": {
            "last": int(vol.iloc[-1]),
            "sma20": int(vol_sma20),
            "ratio": round(vol_ratio, 2)
        },
        "range_52w": {
            "high": round(high_52w, 2),
            "low": round(low_52w, 2),
            "pct_from_high": round(pct_from_52w_high, 2)
        },
        "levels": levels
    }
