"""
EquityLens AI - AnalysisReport Generator (Fase 12)
Orchestrates all analysis modules and assembles the structured AnalysisReport JSON.
All computations are done IN CODE, NOT by Gemini.
"""
from typing import Dict, Any, Optional
from backend.core.cache import cache, now_utc_iso
from backend.providers.yahoo import get_quote, get_history, get_fundamentals, resolve_symbol
from backend.providers.brokerflow import get_broker_flow
from backend.analysis.data_cleaner import clean_ohlcv_dataframe, calculate_data_completeness
from backend.analysis.technicals import calculate_technicals
from backend.analysis.candles import analyze_candlesticks
from backend.analysis.volume import analyze_volume
from backend.analysis.pressure import analyze_buy_sell_pressure
from backend.analysis.fundamentals import analyze_fundamentals
from backend.analysis.banks import is_bank_stock
from backend.analysis.valuation import analyze_valuation
from backend.analysis.plan import generate_trading_plan
from backend.analysis.confluence import calculate_confluence
from backend.analysis.market import analyze_market_regime
from backend.analysis.macro import analyze_macro_sensitivity
from backend.analysis.sentiment import analyze_sentiment
from backend.analysis.forecast.montecarlo import generate_forecast_distribution
from backend.analysis.forecast.baseline import evaluate_model_edge

def generate_analysis_report(
    symbol: str,
    horizon: str = "swing",
    mode: str = "deep",
    capital: float = 100_000_000.0,
    risk_pct: float = 0.01
) -> Dict[str, Any]:
    """
    Master function: assembles the full AnalysisReport from all modules.
    """
    cache_key = f"analysis:{symbol}:{horizon}:{mode}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    market, code = resolve_symbol(symbol)

    # 1. Quote
    quote_data = None
    try:
        quote_data = get_quote(market, code)
    except Exception:
        pass

    # 2. History
    hist_df = None
    clean_meta = {"is_liquid": True, "warnings": []}
    try:
        hist_df = get_history(market, code, period="2y", interval="1d")
        hist_df, clean_meta = clean_ohlcv_dataframe(hist_df, market)
    except Exception:
        pass

    # 3. Fundamentals
    fund_data = None
    try:
        fund_data = get_fundamentals(market, code)
    except Exception:
        pass

    # 4. Technicals
    tech_data = None
    atr = 0.0
    if hist_df is not None and len(hist_df) >= 30:
        try:
            tech_data = calculate_technicals(hist_df)
            atr = tech_data.get("atr14", 0.0)
        except Exception:
            pass

    # 5. Candlestick + Volume
    candle_data = None
    volume_data = None
    if hist_df is not None and len(hist_df) >= 20:
        try:
            candle_data = analyze_candlesticks(hist_df, atr if atr > 0 else 1.0)
        except Exception:
            pass
        try:
            volume_data = analyze_volume(hist_df)
        except Exception:
            pass

    # 6. Buy/Sell Pressure
    pressure_data = None
    if hist_df is not None:
        try:
            pressure_data = analyze_buy_sell_pressure(hist_df)
        except Exception:
            pass

    # 7. Fundamental Analysis (DuPont, Piotroski, Altman, Bank)
    fund_analysis = None
    if fund_data:
        try:
            fund_analysis = analyze_fundamentals(market, code, fund_data)
        except Exception:
            pass

    # 8. Valuation
    val_data = None
    current_price = quote_data["price"] if quote_data else 0.0
    if fund_data:
        try:
            ratios = fund_data.get("ratios", {})
            val_data = analyze_valuation(
                current_price=current_price,
                pe=ratios.get("pe"),
                pbv=ratios.get("pbv"),
                market_cap=fund_data.get("market_cap")
            )
        except Exception:
            pass

    # 9. Broker Flow
    broker_flow = get_broker_flow(code)

    # 10. Data Completeness
    is_bank = is_bank_stock(code, fund_data.get("industry") if fund_data else None)
    completeness = calculate_data_completeness(
        has_quote=quote_data is not None,
        has_history=hist_df is not None and len(hist_df) > 0,
        has_fundamentals=fund_data is not None,
        has_technicals=tech_data is not None,
        has_news=True,  # RSS always available
        has_bank_metrics=False,  # Not yet available from free sources
        is_bank=is_bank,
        has_broker_flow=broker_flow.get("available", False)
    )

    # 11. Trading Plan
    trading_plan = None
    if tech_data and atr > 0:
        supports = tech_data.get("levels", {}).get("support", [])
        resistances = tech_data.get("levels", {}).get("resistance", [])
        try:
            trading_plan = generate_trading_plan(
                current_price=current_price,
                atr=atr,
                support_levels=supports,
                resistance_levels=resistances,
                market=market,
                capital=capital,
                risk_pct=risk_pct,
                horizon=horizon
            )
        except Exception:
            pass

    # 12. Market, Macro & Sentiment (Fase 10)
    market_res = analyze_market_regime(market)
    macro_res = analyze_macro_sensitivity(code, market)
    sentiment_res = analyze_sentiment(code)
    
    # Combined market & macro score
    market_macro_score = round(0.6 * market_res.get("score", 0.0) + 0.4 * macro_res.get("score", 0.0), 2)

    # 13. Confluence
    scores = {
        "technical": tech_data.get("score", 0.0) if tech_data else 0.0,
        "candlestick_volume": candle_data.get("score", 0.0) if candle_data else 0.0,
        "buy_sell_pressure": pressure_data.get("score", 0.0) if pressure_data else 0.0,
        "sentiment": sentiment_res.get("score", 0.0),
        "market_macro": market_macro_score,
        "fundamental": fund_analysis.get("score", 0.0) if fund_analysis else 0.0,
        "valuation": val_data.get("score", 0.0) if val_data else 0.0,
    }

    confluence = calculate_confluence(
        scores=scores,
        horizon=horizon,
        data_completeness_score=completeness["score"],
        has_stale_data=quote_data.get("stale", False) if quote_data else True,
        is_illiquid=not clean_meta.get("is_liquid", True),
    )

    # 13. Probabilistic Forecasting & Edge Evaluation (Fase 11)
    daily_vol = (atr / current_price) if (current_price > 0 and atr > 0) else 0.02
    target_price = trading_plan.get("targets", [{}])[0].get("price", 0.0) if trading_plan else 0.0
    stop_price = trading_plan.get("stop_loss", 0.0) if trading_plan else 0.0
    
    forecast_data = generate_forecast_distribution(
        last_price=current_price,
        daily_vol=daily_vol,
        horizons=[5, 20, 60],
        target=target_price,
        stop=stop_price
    )
    edge_data = evaluate_model_edge(hist_df)
    forecast_data["model_edge"] = edge_data["model_edge"]
    forecast_data["edge_details"] = edge_data

    # Assemble Report
    report = {
        "symbol": f"{market}:{code}",
        "as_of": now_utc_iso(),
        "horizon": horizon,
        "mode": mode,
        "data_completeness": completeness,
        "quote": quote_data,
        "technical": tech_data,
        "candlestick_volume": {
            "patterns": candle_data.get("patterns", []) if candle_data else [],
            "volume": volume_data,
            "score": candle_data.get("score", 0.0) if candle_data else 0.0,
        },
        "buy_sell_pressure": pressure_data,
        "fundamental": fund_analysis,
        "valuation": val_data,
        "market": market_res,
        "macro": macro_res,
        "sentiment": sentiment_res,
        "forecast": forecast_data,
        "trading_plan": trading_plan,
        "confluence": confluence,
        "confidence": confluence["confidence"],
        "broker_flow": broker_flow,
        "data_quality_warnings": clean_meta.get("warnings", []),
        "validator_flags": [],
    }

    # Cache for 15 minutes
    cache.set(cache_key, report, ttl_seconds=900)
    return report
