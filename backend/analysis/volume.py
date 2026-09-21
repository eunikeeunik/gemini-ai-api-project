"""
EquityLens AI - Volume Profile & Flow Analysis (Fase 8)
Calculates Volume Profile (POC, VAH, VAL), OBV, CMF, and Volume-Price Divergence.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List

def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    obv = (np.sign(close.diff().fillna(0)) * volume).cumsum()
    return obv

def compute_cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Chaikin Money Flow (20-day)"""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    vol = df["Volume"]

    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    clv = clv.fillna(0.0)
    mf_vol = clv * vol
    cmf = mf_vol.rolling(period).sum() / vol.rolling(period).sum().replace(0, np.nan)
    return cmf.fillna(0.0)

def compute_volume_profile(df: pd.DataFrame, bins: int = 30) -> Dict[str, Any]:
    """
    Computes Volume Profile:
    - POC (Point of Control): Price bin with the maximum traded volume
    - VAH (Value Area High): Upper boundary of ~70% volume area
    - VAL (Value Area Low): Lower boundary of ~70% volume area
    """
    if len(df) < 20:
        return {"poc": None, "vah": None, "val": None}

    recent = df.tail(60)
    price_min = float(recent["Low"].min())
    price_max = float(recent["High"].max())
    
    if price_max <= price_min:
        return {"poc": price_min, "vah": price_max, "val": price_min}

    bin_edges = np.linspace(price_min, price_max, bins + 1)
    bin_volumes = np.zeros(bins)

    for _, row in recent.iterrows():
        # Distribute bar volume uniformly across [Low, High]
        bar_low, bar_high, bar_vol = row["Low"], row["High"], row["Volume"]
        if bar_high <= bar_low or bar_vol <= 0:
            continue
        for b in range(bins):
            b_low = bin_edges[b]
            b_high = bin_edges[b + 1]
            # Overlap
            overlap = max(0.0, min(bar_high, b_high) - max(bar_low, b_low))
            if overlap > 0:
                fraction = overlap / (bar_high - bar_low)
                bin_volumes[b] += bar_vol * fraction

    max_idx = int(np.argmax(bin_volumes))
    poc_price = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2.0

    total_vol = bin_volumes.sum()
    target_vol = total_vol * 0.70

    # Expand from POC to encompass 70% volume
    left = max_idx
    right = max_idx
    accum_vol = bin_volumes[max_idx]

    while accum_vol < target_vol and (left > 0 or right < bins - 1):
        left_vol = bin_volumes[left - 1] if left > 0 else 0
        right_vol = bin_volumes[right + 1] if right < bins - 1 else 0
        if left_vol >= right_vol and left > 0:
            left -= 1
            accum_vol += left_vol
        elif right < bins - 1:
            right += 1
            accum_vol += right_vol
        else:
            break

    val_price = bin_edges[left]
    vah_price = bin_edges[right + 1]

    return {
        "poc": round(float(poc_price), 2),
        "vah": round(float(vah_price), 2),
        "val": round(float(val_price), 2),
    }

def analyze_volume(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < 20:
        return {"error": "Histori tidak cukup untuk analisis volume"}

    obv_series = compute_obv(df["Close"], df["Volume"])
    cmf_series = compute_cmf(df, 20)
    vp = compute_volume_profile(df, 30)

    cur_cmf = float(cmf_series.iloc[-1])
    obv_trend = "Naik (Akumulasi)" if obv_series.iloc[-1] > obv_series.rolling(20).mean().iloc[-1] else "Turun (Distribusi)"
    
    # Divergence detection
    price_20d_pct = (df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1.0) * 100.0
    vol_20d_ratio = df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]
    
    divergence = "Normal"
    if price_20d_pct > 5.0 and cur_cmf < -0.05:
        divergence = "Bearish Divergence: Harga naik tapi Money Flow negatif (reli rentan)"
    elif price_20d_pct < -5.0 and cur_cmf > 0.05:
        divergence = "Bullish Divergence: Harga terkoreksi tapi akumulasi terdeteksi (potensi rebound)"

    return {
        "obv_trend": obv_trend,
        "cmf_20": round(cur_cmf, 2),
        "divergence": divergence,
        "volume_profile": vp
    }
