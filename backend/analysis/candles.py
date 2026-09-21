"""
EquityLens AI - Candlestick Recognition & Statistical Backtest (Fase 8)
Detects patterns, calculates context score (0 to 1), and tests 5-year historical hit rate.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

def detect_candlestick_patterns(df: pd.DataFrame, atr: float) -> List[Dict[str, Any]]:
    """Detects major patterns on recent candles and calculates context-aware scores"""
    if len(df) < 5:
        return []

    patterns = []
    
    # We inspect the latest completed candle (or current bar)
    c0 = df.iloc[-1]
    c1 = df.iloc[-2] if len(df) > 1 else c0
    c2 = df.iloc[-3] if len(df) > 2 else c1

    open_0, high_0, low_0, close_0 = c0["Open"], c0["High"], c0["Low"], c0["Close"]
    vol_0 = c0["Volume"]
    body_0 = abs(close_0 - open_0)
    range_0 = high_0 - low_0
    is_bull_0 = close_0 >= open_0

    open_1, close_1 = c1["Open"], c1["Close"]
    body_1 = abs(close_1 - open_1)
    is_bull_1 = close_1 >= open_1

    # 1. Doji
    if range_0 > 0 and body_0 <= (range_0 * 0.10):
        patterns.append({
            "name": "Doji",
            "direction": "neutral",
            "date": str(c0.name)[:10],
            "description": "Keseimbangan antara pembeli dan penjual (indecision)",
            "context_score": 0.4 if range_0 > atr * 0.8 else 0.2,
            "confirmed": False
        })

    # 2. Hammer (Bullish Reversal)
    lower_shadow_0 = min(open_0, close_0) - low_0
    upper_shadow_0 = high_0 - max(open_0, close_0)
    if lower_shadow_0 >= (2.0 * body_0) and upper_shadow_0 <= (0.5 * body_0) and body_0 > 0:
        patterns.append({
            "name": "Hammer",
            "direction": "bullish",
            "date": str(c0.name)[:10],
            "description": "Penolakan harga rendah oleh buyer setelah fase tekanan jual",
            "context_score": 0.75 if close_0 > c1["Close"] else 0.50,
            "confirmed": close_0 > open_0
        })

    # 3. Shooting Star (Bearish Reversal)
    if upper_shadow_0 >= (2.0 * body_0) and lower_shadow_0 <= (0.5 * body_0) and body_0 > 0:
        patterns.append({
            "name": "Shooting Star",
            "direction": "bearish",
            "date": str(c0.name)[:10],
            "description": "Penolakan harga tinggi oleh seller di area resistensi",
            "context_score": 0.70 if close_0 < c1["Close"] else 0.45,
            "confirmed": close_0 < open_0
        })

    # 4. Bullish Engulfing
    if not is_bull_1 and is_bull_0 and (open_0 <= close_1) and (close_0 >= open_1) and body_0 > body_1:
        patterns.append({
            "name": "Bullish Engulfing",
            "direction": "bullish",
            "date": str(c0.name)[:10],
            "description": "Candle hijau besar menelan penuh candle merah sebelumnya",
            "context_score": 0.85 if vol_0 > df["Volume"].tail(20).mean() else 0.60,
            "confirmed": True
        })

    # 5. Bearish Engulfing
    if is_bull_1 and not is_bull_0 and (open_0 >= close_1) and (close_0 <= open_1) and body_0 > body_1:
        patterns.append({
            "name": "Bearish Engulfing",
            "direction": "bearish",
            "date": str(c0.name)[:10],
            "description": "Candle merah besar menelan penuh candle hijau sebelumnya",
            "context_score": 0.85 if vol_0 > df["Volume"].tail(20).mean() else 0.60,
            "confirmed": True
        })

    return patterns

def backtest_candlestick_pattern_5y(df: pd.DataFrame, pattern_name: str, horizon_days: int = 5) -> Dict[str, Any]:
    """
    Tests historical occurrence of the specified pattern in the stock over 5 years.
    Evaluates whether the move was profitable in the anticipated direction.
    """
    if len(df) < 50:
        return {"n_events": 0, "hit_rate": 0.0, "status": "sampel kecil, tidak signifikan"}

    events = 0
    successes = 0

    closes = df["Close"].values
    opens = df["Open"].values
    highs = df["High"].values
    lows = df["Low"].values

    for i in range(2, len(df) - horizon_days):
        body = abs(closes[i] - opens[i])
        rng = highs[i] - lows[i]
        matched = False
        is_bullish = True

        if pattern_name == "Hammer":
            lower_shadow = min(opens[i], closes[i]) - lows[i]
            upper_shadow = highs[i] - max(opens[i], closes[i])
            if lower_shadow >= 2 * body and upper_shadow <= 0.5 * body and body > 0:
                matched = True
                is_bullish = True

        elif pattern_name == "Shooting Star":
            lower_shadow = min(opens[i], closes[i]) - lows[i]
            upper_shadow = highs[i] - max(opens[i], closes[i])
            if upper_shadow >= 2 * body and lower_shadow <= 0.5 * body and body > 0:
                matched = True
                is_bullish = False

        elif pattern_name == "Bullish Engulfing":
            if (closes[i-1] < opens[i-1]) and (closes[i] > opens[i]) and (opens[i] <= closes[i-1]) and (closes[i] >= opens[i-1]):
                matched = True
                is_bullish = True

        elif pattern_name == "Bearish Engulfing":
            if (closes[i-1] > opens[i-1]) and (closes[i] < opens[i]) and (opens[i] >= closes[i-1]) and (closes[i] <= opens[i-1]):
                matched = True
                is_bullish = False

        if matched:
            events += 1
            future_return = (closes[i + horizon_days] - closes[i]) / closes[i]
            if (is_bullish and future_return > 0.005) or (not is_bullish and future_return < -0.005):
                successes += 1

    if events == 0:
        return {"n_events": 0, "hit_rate": 0.0, "status": "Pola tidak pernah terdeteksi pada histori"}

    hit_rate = round(successes / events, 2)
    status = "Signifikan" if events >= 20 else "sampel kecil, tidak signifikan"

    return {
        "pattern": pattern_name,
        "n_events": events,
        "successes": successes,
        "hit_rate": hit_rate,
        "horizon_days": horizon_days,
        "status": status
    }

def analyze_candlesticks(df: pd.DataFrame, atr: float) -> Dict[str, Any]:
    patterns = detect_candlestick_patterns(df, atr)
    pattern_results = []
    
    overall_candle_score = 0.0
    for p in patterns:
        stats = backtest_candlestick_pattern_5y(df, p["name"])
        p["stats_5y"] = stats
        pattern_results.append(p)
        
        weight = p["context_score"]
        if p["direction"] == "bullish":
            overall_candle_score += 0.3 * weight
        elif p["direction"] == "bearish":
            overall_candle_score -= 0.3 * weight

    return {
        "patterns": pattern_results,
        "score": round(max(-1.0, min(1.0, overall_candle_score)), 2)
    }
