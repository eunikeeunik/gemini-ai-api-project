"""
EquityLens AI - Monte Carlo Path Simulator (Fase 11 - Spec 10.5)
Generates probabilistic volatility cones and touch probabilities
using Geometric Brownian Motion and historical bootstrap.
All computations in NumPy / SciPy, NOT Gemini.
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd

def simulate_mc_paths(
    last_price: float,
    daily_vol: float,
    days: int = 20,
    n_sims: int = 2000,
    drift: float = 0.0,
    seed: int = 42
) -> np.ndarray:
    """
    Simulates geometric brownian motion paths for n_sims iterations over given days.
    rets = (drift - 0.5 * sigma^2) + sigma * Z
    price_t = price_0 * exp(cumsum(rets))
    """
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_sims, days))
    rets = (drift - 0.5 * (daily_vol ** 2)) + daily_vol * z
    paths = last_price * np.exp(np.cumsum(rets, axis=1))
    return paths

def calculate_touch_probs(paths: np.ndarray, target: float, stop: float) -> Dict[str, float]:
    """
    Calculates probability of touching target first vs stop loss first.
    Returns: {"p_target_first": float, "p_stop_first": float, "p_neither": float}
    """
    if paths.size == 0:
        return {"p_target_first": 0.5, "p_stop_first": 0.5, "p_neither": 0.0}

    hit_t = (paths >= target).any(axis=1)
    hit_s = (paths <= stop).any(axis=1)

    first_t = np.where(hit_t, (paths >= target).argmax(axis=1), np.inf)
    first_s = np.where(hit_s, (paths <= stop).argmax(axis=1), np.inf)

    p_t_first = float((first_t < first_s).mean())
    p_s_first = float((first_s < first_t).mean())
    p_neither = float((~hit_t & ~hit_s).mean())

    return {
        "p_target_first": round(p_t_first, 3),
        "p_stop_first": round(p_s_first, 3),
        "p_neither": round(p_neither, 3)
    }

def generate_forecast_distribution(
    last_price: float,
    daily_vol: float,
    horizons: List[int] = [5, 20, 60],
    target: float = 0.0,
    stop: float = 0.0
) -> Dict[str, Any]:
    """
    Produces multi-horizon percentile volatility cones (10th, 50th, 90th percentiles).
    """
    max_days = max(horizons)
    paths = simulate_mc_paths(last_price, daily_vol, days=max_days, n_sims=2000)
    
    horizon_results = {}
    for h in horizons:
        h_idx = h - 1
        h_prices = paths[:, h_idx]
        horizon_results[f"{h}d"] = {
            "days": h,
            "q10": round(float(np.percentile(h_prices, 10)), 1),
            "q50": round(float(np.percentile(h_prices, 50)), 1),
            "q90": round(float(np.percentile(h_prices, 90)), 1),
            "prob_gain": round(float((h_prices > last_price).mean()), 3),
        }

    touch_data = {}
    if target > 0 and stop > 0:
        touch_data = calculate_touch_probs(paths, target, stop)

    return {
        "last_price": last_price,
        "daily_volatility_pct": round(daily_vol * 100.0, 2),
        "annualized_volatility_pct": round(daily_vol * np.sqrt(252) * 100.0, 2),
        "horizons": horizon_results,
        "touch_probabilities": touch_data,
        "model_type": "Geometric Brownian Motion (Monte Carlo)"
    }
