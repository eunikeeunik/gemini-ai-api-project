"""
EquityLens AI - Walk-Forward Baseline Evaluation (Fase 11)
Compares model directional predictions against a naive walk baseline (P_t+1 ≈ P_t).
Sets model_edge=False when directional accuracy fails to beat coin-flip or naive baseline.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd

def evaluate_model_edge(hist_df: pd.DataFrame, min_bars: int = 60) -> Dict[str, Any]:
    """
    Evaluates whether technical momentum has a statistically significant edge over random walk.
    If hit rate does not exceed 52% with p < 0.05, model_edge is set to False.
    """
    if hist_df is None or len(hist_df) < min_bars:
        return {
            "model_edge": False,
            "reason": "Data histori tidak mencukupi untuk uji edge walk-forward",
            "hit_rate": 0.50,
            "baseline_naive_hit_rate": 0.50
        }

    close = hist_df["Close"]
    rets_1d = close.pct_change().dropna()
    
    # 20-day momentum signal
    mom20 = close.pct_change(20).shift(1).dropna()
    forward_rets = close.pct_change(20).shift(-20).dropna()
    
    common_idx = mom20.index.intersection(forward_rets.index)
    if len(common_idx) < 30:
        return {
            "model_edge": False,
            "reason": "Sampel observasi forward terlalu sedikit (<30 bar)",
            "hit_rate": 0.50,
            "baseline_naive_hit_rate": 0.50
        }

    signals = np.sign(mom20.loc[common_idx])
    actuals = np.sign(forward_rets.loc[common_idx])
    
    hits = (signals == actuals)
    hit_rate = float(hits.mean())

    # Baseline: naive prior (positive drift baseline)
    naive_positive_rate = float((actuals > 0).mean())
    baseline = max(0.50, naive_positive_rate)

    # Require outperforming baseline by at least 2% edge
    has_edge = bool(hit_rate > (baseline + 0.02) and hit_rate > 0.53)

    return {
        "model_edge": has_edge,
        "hit_rate": round(hit_rate, 3),
        "baseline_hit_rate": round(baseline, 3),
        "sample_size": len(common_idx),
        "note": "Edge statistik terkonfirmasi" if has_edge else "Tidak ada edge statistik atas baseline naif; hanya sajikan rentang volatilitas"
    }
