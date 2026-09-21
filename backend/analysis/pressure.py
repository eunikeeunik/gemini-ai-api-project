"""
EquityLens AI - Buy/Sell Pressure Analysis (Fase 8)
Computes proxy buying vs selling pressure from OHLCV and marks source honestly.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

def analyze_buy_sell_pressure(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < 15:
        return {
            "score": 0.0,
            "basis": "proxy",
            "sources_used": ["ohlcv"],
            "verdict": "Data tidak mencukupi"
        }

    recent = df.tail(15)
    close = recent["Close"]
    high = recent["High"]
    low = recent["Low"]
    volume = recent["Volume"]

    # Close Location Value (CLV): where close sits within [Low, High]
    # +1 = closed at High (aggressive buying), -1 = closed at Low (aggressive selling)
    rng = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / rng
    clv = clv.fillna(0.0)

    # Volume-weighted CLV
    weighted_clv = (clv * volume).sum() / volume.sum() if volume.sum() > 0 else 0.0

    # Up-volume vs Down-volume ratio
    up_bars = recent[recent["Close"] > recent["Open"]]
    down_bars = recent[recent["Close"] < recent["Open"]]
    up_vol = up_bars["Volume"].sum()
    down_vol = down_bars["Volume"].sum()
    total_vol = up_vol + down_vol
    
    vol_imbalance = (up_vol - down_vol) / total_vol if total_vol > 0 else 0.0

    pressure_score = (weighted_clv * 0.5) + (vol_imbalance * 0.5)
    pressure_score = round(max(-1.0, min(1.0, float(pressure_score))), 2)

    if pressure_score > 0.35:
        verdict = "Dominasi Tekanan Beli Kuat (Akumulasi Aktif)"
    elif pressure_score > 0.10:
        verdict = "Tekanan Beli Moderat"
    elif pressure_score < -0.35:
        verdict = "Dominasi Tekanan Jual Kuat (Distribusi Aktif)"
    elif pressure_score < -0.10:
        verdict = "Tekanan Jual Moderat"
    else:
        verdict = "Tekanan Seimbang (Konsolidasi Netral)"

    return {
        "score": pressure_score,
        "basis": "proxy",
        "sources_used": ["ohlcv_price_action_and_volume"],
        "verdict": verdict,
        "metrics": {
            "up_volume_pct": round((up_vol / total_vol) * 100.0, 1) if total_vol > 0 else 50.0,
            "down_volume_pct": round((down_vol / total_vol) * 100.0, 1) if total_vol > 0 else 50.0,
            "weighted_clv": round(float(weighted_clv), 2)
        }
    }
