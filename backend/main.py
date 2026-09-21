"""
EquityLens AI - FastAPI Application Entry Point
Exposes comprehensive financial analysis APIs and chat endpoints,
serving live data, technical/fundamental engines, and streaming LLM narratives.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse

from backend.core.config import settings
from backend.core.errors import EquityLensError
from backend.core.calendar import get_market_status
from backend.providers.yahoo import (
    get_quote,
    get_history,
    get_fundamentals,
    get_market_overview,
    resolve_symbol
)
from backend.providers.news_rss import get_cached_news
from backend.providers.brokerflow import get_broker_flow
from backend.analysis.report import generate_analysis_report
from backend.analysis.technicals import calculate_technicals
from backend.analysis.candles import analyze_candlesticks
from backend.analysis.volume import analyze_volume
from backend.analysis.pressure import analyze_buy_sell_pressure
from backend.analysis.fundamentals import analyze_fundamentals
from backend.analysis.valuation import analyze_valuation
from backend.agent.gemini_agent import gemini_agent
from backend.backtest.engine import backtest_engine
from backend.analysis.portfolio import analyze_portfolio_risk
from backend.providers.macro_fred_bps import get_macro_snapshot
from backend.providers.av_gateway import av_gateway
from backend.analysis.ledger import ledger

# Initialize FastAPI App
app = FastAPI(
    title="EquityLens AI — Financial Intelligence Engine",
    description="Institutional-grade stock analysis and valuation engine covering IDX, US, SGX, and China markets.",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for EquityLens custom exceptions
@app.exception_handler(EquityLensError)
async def equitylens_error_handler(request: Request, exc: EquityLensError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# --- Core & Health Endpoints ---

@app.get("/api/health")
async def health_check():
    """Health check endpoint displaying system status and configured markets."""
    return {
        "status": "healthy",
        "service": "EquityLens AI Engine",
        "version": "2.0.0",
        "markets": {
            "IDX": get_market_status("IDX"),
            "US": get_market_status("US"),
            "SGX": get_market_status("SGX"),
            "SSE": get_market_status("SSE")
        }
    }


# --- Quotes & Market Data Endpoints ---

@app.get("/api/quote")
async def api_get_quote(symbol: str = Query(..., description="Stock symbol, e.g. BBCA, IDX:BBCA, AAPL")):
    """Get real-time quote for a single stock."""
    try:
        market, code = resolve_symbol(symbol)
        quote = get_quote(market, code)
        return quote
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch quote for '{symbol}': {str(e)}")


@app.get("/api/stock/{symbol}")
async def api_get_stock_legacy(symbol: str):
    """Compatibility alias for legacy /api/stock/:symbol calls."""
    try:
        market, code = resolve_symbol(symbol)
        quote = get_quote(market, code)
        return {
            "symbol": quote.get("yahoo_ticker", symbol),
            "name": quote.get("name", symbol),
            "currency": quote.get("currency", "IDR"),
            "price": quote.get("price"),
            "change": quote.get("change"),
            "changePercent": f"{quote.get('change_pct', 0.0):+.2f}%",
            "dayRange": f"{quote.get('day_low', '-')} - {quote.get('day_high', '-')}",
            "fiftyTwoWeekRange": f"{quote.get('fifty_two_week_low', '-')} - {quote.get('fifty_two_week_high', '-')}",
            "pe": str(quote.get("pe", "N/A")),
            "pbv": str(quote.get("pbv", "N/A")),
            "marketCap": quote.get("market_cap")
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found: {str(e)}")


@app.get("/api/quotes")
async def api_get_quotes(symbols: str = Query(..., description="Comma-separated stock symbols for ticker/watchlist")):
    """Batch fetch quotes for multiple tickers (used by live ticker bar)."""
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        return []
    
    results = []
    for sym in sym_list:
        try:
            market, code = resolve_symbol(sym)
            q = get_quote(market, code)
            results.append(q)
        except Exception:
            results.append({"symbol": sym, "price": None, "change_pct": 0.0, "status": "unavailable"})
    return results


@app.get("/api/history")
async def api_get_history(
    symbol: str = Query(...),
    period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y|10y|max)$"),
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$")
):
    """Get historical OHLCV data."""
    try:
        market, code = resolve_symbol(symbol)
        df = get_history(market, code, period=period, interval=interval)
        if df.empty:
            raise HTTPException(status_code=404, detail="No historical data found")
        
        # Convert dataframe to JSON records
        df_reset = df.reset_index()
        records = []
        for _, row in df_reset.iterrows():
            d_val = row.get("Date")
            date_str = d_val.isoformat() if hasattr(d_val, "isoformat") else str(d_val)
            records.append({
                "date": date_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if "Volume" in row else 0
            })
        return {"symbol": symbol, "count": len(records), "history": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Analysis Modules Endpoints ---

@app.get("/api/technicals")
async def api_get_technicals(symbol: str = Query(...)):
    """Calculate technical indicators (RSI, MACD, Bollinger, ATR, MAs, S/R)."""
    market, code = resolve_symbol(symbol)
    df = get_history(market, code, period="2y", interval="1d")
    if df.empty or len(df) < 20:
        raise HTTPException(status_code=400, detail="Insufficient price history for technical calculations")
    return calculate_technicals(df)


@app.get("/api/fundamentals")
async def api_get_fundamentals(symbol: str = Query(...)):
    """Analyze financial statements (DuPont, Piotroski, Altman Z, Bank NIM/NPL/CAR)."""
    market, code = resolve_symbol(symbol)
    fund = get_fundamentals(market, code)
    return analyze_fundamentals(fund, market=market, symbol=code)


@app.get("/api/valuation")
async def api_get_valuation(symbol: str = Query(...)):
    """Valuation percentiles (PER/PBV 5-year), Graham Number, DCF sensitivity."""
    market, code = resolve_symbol(symbol)
    fund = get_fundamentals(market, code)
    quote = get_quote(market, code)
    return analyze_valuation(fund, quote, market=market)


@app.get("/api/candlestick-volume")
async def api_get_candlestick_volume(symbol: str = Query(...)):
    """Candlestick patterns with historical win rate + Volume Profile (POC/VAH/VAL)."""
    market, code = resolve_symbol(symbol)
    df = get_history(market, code, period="2y", interval="1d")
    tech = calculate_technicals(df)
    atr = tech.get("atr14", 1.0)
    candles = analyze_candlesticks(df, atr)
    volume = analyze_volume(df)
    return {"candlestick": candles, "volume": volume}


@app.get("/api/pressure")
async def api_get_pressure(symbol: str = Query(...)):
    """Calculate buying vs selling pressure proxy from CLV and volume imbalance."""
    market, code = resolve_symbol(symbol)
    df = get_history(market, code, period="6mo", interval="1d")
    return analyze_buy_sell_pressure(df)


@app.get("/api/news")
async def api_get_news(symbol: Optional[str] = Query(None), limit: int = Query(6, ge=1, le=20)):
    """Get aggregated RSS news with deduplication and simple sentiment."""
    return get_cached_news(symbol=symbol, limit=limit)


@app.get("/api/market-overview")
async def api_get_market_overview():
    """Get broad market index overview (IHSG, S&P 500, STI, SSE, USD/IDR)."""
    return get_market_overview()


@app.get("/api/brokerflow")
async def api_get_brokerflow(symbol: str = Query(...)):
    """Check broker flow status (NullBrokerFlow returns available: false)."""
    return get_broker_flow(symbol)


@app.get("/api/analysis")
async def api_get_analysis(
    symbol: str = Query(..., description="Stock symbol, e.g. BBCA, IDX:BBRI, AAPL"),
    horizon: str = Query("swing", pattern="^(swing|positional|long_term)$"),
    mode: str = Query("deep", pattern="^(deep|brief)$"),
    capital: float = Query(100_000_000.0, ge=1_000_000.0),
    risk_pct: float = Query(0.01, ge=0.001, le=0.1)
):
    """
    Master AnalysisReport endpoint (Fase 12).
    Assembles technicals, candlestick/volume, buy/sell pressure, fundamentals,
    valuation, trading plan, confluence scores, data completeness, and confidence.
    """
    try:
        report = generate_analysis_report(
            symbol=symbol,
            horizon=horizon,
            mode=mode,
            capital=capital,
            risk_pct=risk_pct
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis calculation error: {str(e)}")


# --- Phase 14-17 Endpoints (Backtest, Portfolio Risk, Macro & Quota) ---

@app.get("/api/backtest")
async def api_run_backtest(
    symbol: str = Query(...),
    market: str = Query("IDX"),
    capital: float = Query(100_000_000.0),
    risk_pct: float = Query(0.01)
):
    """Executes walk-forward backtest of trading plan rules without look-ahead bias."""
    m, c = resolve_symbol(symbol)
    df = get_history(m, c, period="2y", interval="1d")
    return backtest_engine.run_backtest(
        df=df,
        market=m,
        initial_capital=capital,
        risk_per_trade_pct=risk_pct
    )


@app.get("/api/portfolio")
async def api_portfolio_risk(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. BBCA,BBRI,BMRI"),
    weights: Optional[str] = Query(None, description="Comma-separated weights, e.g. 0.4,0.3,0.3")
):
    """Computes VaR 95%, CVaR, Drawdown, correlation, and PyPortfolioOpt allocation."""
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    weight_list = [float(w.strip()) for w in weights.split(",")] if weights else None
    return analyze_portfolio_risk(symbols=sym_list, weights=weight_list)


@app.get("/api/macro")
async def api_get_macro():
    """Get unified macroeconomic snapshot (FRED + BPS)."""
    return await get_macro_snapshot()


@app.get("/api/av-quota")
async def api_get_av_quota():
    """Get Alpha Vantage QuotaGuard tracking status (25 req/day ceiling)."""
    return av_gateway.guard.get_quota_status()


@app.get("/api/track-record")
async def api_get_track_record(symbol: Optional[str] = Query(None)):
    """Get empirical prediction ledger track record and running hit-rate."""
    return ledger.get_track_record(symbol=symbol)



# --- Chat & AI Assistant Endpoints ---

@app.post("/api/chat")
async def api_chat(request: Request):
    """
    Intelligent equity analyst chat endpoint.
    Supports both standard JSON request/response and streaming SSE.
    Compatible with existing frontend format: { conversation: [{role, text}] }
    or new format: { message: str, stream: bool }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Extract user message
    user_msg = ""
    history = []
    is_streaming = body.get("stream", False)

    if "conversation" in body and isinstance(body["conversation"], list):
        conv = body["conversation"]
        for item in conv:
            if item.get("role") == "user":
                user_msg = item.get("text", "")
            history.append({"role": item.get("role", "user"), "text": item.get("text", "")})
    elif "message" in body:
        user_msg = body.get("message", "")
    
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty user message")

    if is_streaming:
        async def event_generator():
            try:
                async for chunk in gemini_agent.chat_stream(user_msg, history=history):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        chat_resp = await gemini_agent.chat(user_msg, history=history)
        return {
            "result": chat_resp.get("text", ""),
            "validation": chat_resp.get("validation", {})
        }


# --- Static Files Mounting ---
# Serve frontend from gemini-chatbot-api/public
static_path = Path(settings.STATIC_DIR)
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
