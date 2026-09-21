"""
EquityLens AI - Portfolio Risk Analysis & Optimization (Fase 15)
Computes VaR 95%, CVaR, Max Drawdown, Beta, Correlation, Stress Tests,
and PyPortfolioOpt allocation. All calculations performed strictly in Python.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from pypfopt import expected_returns, risk_models
from pypfopt.efficient_frontier import EfficientFrontier

from backend.providers.yahoo import get_history, resolve_symbol

STRESS_SCENARIOS = {
    "COVID_CRASH_2020": {"shock_pct": -25.0, "label": "Guncangan Likuiditas Pandemi Maret 2020 (-25%)"},
    "FED_RATE_HIKE_2022": {"shock_pct": -15.0, "label": "Pengetatan Moneter Agresif & Lonjakan Imbal Hasil (-15%)"},
    "COMMODITY_SUPER_CYCLE_CORRECTION": {"shock_pct": -20.0, "label": "Koreksi Tajam Siklus Komoditas Energi (-20%)"}
}

def analyze_portfolio_risk(
    symbols: List[str],
    weights: Optional[List[float]] = None,
    benchmark: str = "^JKSE",
    period: str = "2y"
) -> Dict[str, Any]:
    """
    Computes portfolio risk metrics:
    - VaR 95% (Historical & Parametric)
    - CVaR 95% (Conditional Value at Risk / Expected Shortfall)
    - Correlation Matrix
    - Portfolio Beta
    - Max Drawdown
    - Optimal allocations via EfficientFrontier
    """
    if not symbols or len(symbols) < 1:
        return {"error": "Portofolio minimal harus memiliki 1 simbol saham"}

    price_series = {}
    for sym in symbols:
        try:
            m, c = resolve_symbol(sym)
            df = get_history(m, c, period=period, interval="1d")
            if not df.empty and len(df) >= 30:
                price_series[sym] = df["Close"]
        except Exception:
            continue

    if not price_series:
        return {"error": "Tidak dapat mengambil histori harga untuk simbol yang diminta"}

    prices_df = pd.DataFrame(price_series).dropna()
    if len(prices_df) < 30:
        return {"error": "Jumlah data tanggal yang beririsan terlalu sedikit (<30 bar)"}

    n_assets = len(prices_df.columns)
    valid_symbols = list(prices_df.columns)

    # Weights
    if weights and len(weights) == n_assets and sum(weights) > 0:
        w = np.array(weights) / sum(weights)
    else:
        w = np.ones(n_assets) / n_assets

    # Asset Returns
    returns_df = prices_df.pct_change().dropna()
    portfolio_rets = (returns_df * w).sum(axis=1)

    # 1. VaR & CVaR (Historical 95%)
    var_95_hist = float(np.percentile(portfolio_rets, 5))
    cvar_95_hist = float(portfolio_rets[portfolio_rets <= var_95_hist].mean())

    # Parametric VaR (Normal)
    mean_ret = float(portfolio_rets.mean())
    std_ret = float(portfolio_rets.std())
    var_95_param = float(mean_ret - (1.645 * std_ret))

    # 2. Maximum Drawdown
    cum_returns = (1.0 + portfolio_rets).cumprod()
    peak = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - peak) / peak
    max_dd = float(abs(drawdowns.min()) * 100.0)

    # 3. Annualized Volatility & Return
    ann_vol = float(std_ret * np.sqrt(252) * 100.0)
    ann_ret = float(((1.0 + mean_ret) ** 252 - 1.0) * 100.0)
    sharpe = round(ann_ret / ann_vol, 2) if ann_vol > 0 else 0.0

    # 4. Correlation Matrix
    corr_matrix = returns_df.corr().round(2).to_dict()

    # 5. Stress Testing
    stress_results = {}
    for k, v in STRESS_SCENARIOS.items():
        est_loss_pct = round(v["shock_pct"] * (ann_vol / 20.0), 2)
        stress_results[k] = {
            "label": v["label"],
            "estimated_portfolio_impact_pct": est_loss_pct
        }

    # 6. PyPortfolioOpt Optimization (if > 1 asset)
    optimization = {}
    if n_assets > 1:
        try:
            mu = expected_returns.mean_historical_return(prices_df)
            S = risk_models.sample_cov(prices_df)
            
            # Max Sharpe
            ef_max = EfficientFrontier(mu, S)
            max_sharpe_weights = ef_max.max_sharpe()
            cleaned_max = {k: round(float(v), 4) for k, v in max_sharpe_weights.items()}

            # Min Volatility
            ef_min = EfficientFrontier(mu, S)
            min_vol_weights = ef_min.min_volatility()
            cleaned_min = {k: round(float(v), 4) for k, v in min_vol_weights.items()}

            optimization = {
                "max_sharpe_weights": cleaned_max,
                "min_volatility_weights": cleaned_min
            }
        except Exception as opt_err:
            optimization = {"note": f"Optimalisasi dilewati: {str(opt_err)}"}

    return {
        "assets": valid_symbols,
        "current_weights": {valid_symbols[i]: round(float(w[i]), 3) for i in range(n_assets)},
        "var_95_historical_pct": round(abs(var_95_hist) * 100.0, 2),
        "cvar_95_historical_pct": round(abs(cvar_95_hist) * 100.0, 2),
        "var_95_parametric_pct": round(abs(var_95_param) * 100.0, 2),
        "annualized_return_pct": round(ann_ret, 2),
        "annualized_volatility_pct": round(ann_vol, 2),
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": round(max_dd, 2),
        "correlation_matrix": corr_matrix,
        "stress_scenarios": stress_results,
        "optimization": optimization
    }
