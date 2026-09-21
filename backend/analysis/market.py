"""
EquityLens AI - Market Regime & Breadth Analysis (Fase 10)
Analyzes broad market benchmark (IHSG for IDX, S&P 500 for US, etc.)
to determine risk regime: risk_on, risk_off, or neutral.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd
from backend.providers.yahoo import get_history, get_quote

BENCHMARKS = {
    "IDX": "^JKSE",
    "US": "^GSPC",
    "SGX": "^STI",
    "SSE": "000001.SS"
}

def analyze_market_regime(market: str = "IDX") -> Dict[str, Any]:
    """
    Evaluates market regime using benchmark index trend, moving averages, and volatility.
    Score ranges from -1.0 (strong risk-off / bear) to +1.0 (strong risk-on / bull).
    """
    market = market.upper()
    bench_code = BENCHMARKS.get(market, "^JKSE")
    
    try:
        df = get_history(market, bench_code, period="1y", interval="1d")
        if df.empty or len(df) < 50:
            return {"market": market, "regime": "neutral", "score": 0.0, "details": "Data histori indeks tidak mencukupi"}
        
        close = df["Close"]
        current = float(close.iloc[-1])
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma50
        
        # Volatility: annualized 20-day standard deviation of returns
        rets = close.pct_change().dropna()
        ann_vol = float(rets.tail(20).std() * np.sqrt(252) * 100.0)

        # Scoring
        score = 0.0
        # Price above MAs
        if current > sma50:
            score += 0.35
        else:
            score -= 0.35
            
        if current > sma200:
            score += 0.35
        else:
            score -= 0.35
            
        if sma20 > sma50:
            score += 0.20
        else:
            score -= 0.20

        # Volatility penalty (elevated vol indicates market stress)
        if ann_vol > 25.0:
            score -= 0.20
        elif ann_vol < 15.0:
            score += 0.10

        score = float(np.clip(score, -1.0, 1.0))
        
        if score >= 0.25:
            regime = "risk_on"
        elif score <= -0.25:
            regime = "risk_off"
        else:
            regime = "neutral"

        return {
            "market": market,
            "benchmark": bench_code,
            "current_index": round(current, 2),
            "regime": regime,
            "score": round(score, 2),
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "annualized_volatility_pct": round(ann_vol, 2),
            "as_of": str(df.index[-1])[:10]
        }
    except Exception as e:
        return {
            "market": market,
            "regime": "neutral",
            "score": 0.0,
            "error": str(e),
            "note": "Analisis pasar menggunakan fallback netral"
        }
