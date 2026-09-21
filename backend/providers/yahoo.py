"""
EquityLens AI - Yahoo Finance Adapter
Handles real-time and historical quotes, fundamentals, and market indices
with caching, throttle protection, and honest error handling.
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import re
from backend.core.cache import cache, now_utc_iso
from backend.core.calendar import get_market_status
from backend.core.errors import ProviderError, DataNotFoundError

SUFFIX_MAP = {
    "IDX": ".JK",
    "SGX": ".SI",
    "SSE": ".SS",
    "SZSE": ".SZ",
    "US": "",
}

INDEX_MAP = {
    "IHSG": ("IDX", "^JKSE"),
    "^JKSE": ("IDX", "^JKSE"),
    "LQ45": ("IDX", "^JKLQ45"),
    "^JKLQ45": ("IDX", "^JKLQ45"),
    "STI": ("SGX", "^STI"),
    "^STI": ("SGX", "^STI"),
    "SP500": ("US", "^GSPC"),
    "^GSPC": ("US", "^GSPC"),
    "NASDAQ": ("US", "^IXIC"),
    "^IXIC": ("US", "^IXIC"),
    "SSE": ("SSE", "000001.SS"),
    "000001.SS": ("SSE", "000001.SS"),
    "USDIDR": ("US", "USDIDR=X"),
    "VIX": ("US", "^VIX"),
    "OIL": ("US", "CL=F"),
    "GOLD": ("US", "GC=F"),
}

COMMON_US_TICKERS = {
    "AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC",
    "NFLX", "SPY", "QQQ", "DIA", "IWM", "JPM", "BAC", "WFC", "C", "GS", "MS",
    "DIS", "V", "MA", "PYPL", "COIN", "PLTR", "UBER", "ABNB", "CRM", "ORCL",
    "CSCO", "IBM", "BABA", "PDD", "JD", "NIO", "XOM", "CVX", "KO", "PEP", "WMT", "COST"
}

def resolve_symbol(raw: str) -> Tuple[str, str]:
    """Resolves arbitrary user ticker input into (market, code)"""
    cleaned = raw.strip().upper()
    if cleaned in INDEX_MAP:
        return INDEX_MAP[cleaned]

    if ":" in cleaned:
        parts = cleaned.split(":", 1)
        market = parts[0].upper()
        code = parts[1].upper()
        if market in SUFFIX_MAP:
            return market, code

    if cleaned.endswith(".JK"):
        return "IDX", cleaned[:-3]
    if cleaned.endswith(".SI"):
        return "SGX", cleaned[:-3]
    if cleaned.endswith(".SS"):
        return "SSE", cleaned[:-3]
    if cleaned.endswith(".SZ"):
        return "SZSE", cleaned[:-3]

    if cleaned in COMMON_US_TICKERS:
        return "US", cleaned

    # Indonesian stock heuristics: 4 alphabetic characters
    if len(cleaned) == 4 and cleaned.isalpha():
        return "IDX", cleaned

    # Fallback to US
    return "US", cleaned

def to_yahoo_ticker(market: str, code: str) -> str:
    market = market.upper()
    code = code.upper()
    if code.startswith("^") or code.endswith("=X") or code.endswith("=F") or ".SS" in code or ".SZ" in code or ".JK" in code:
        return code
    suffix = SUFFIX_MAP.get(market, "")
    return f"{code}{suffix}"

def get_quote(market: str, code: str) -> Dict[str, Any]:
    market = market.upper()
    code = code.upper()
    cache_key = f"quote:{market}:{code}"
    
    cached = cache.get(cache_key)
    if cached:
        return cached

    yahoo_sym = to_yahoo_ticker(market, code)
    mkt_status = get_market_status(market)

    try:
        ticker = yf.Ticker(yahoo_sym)
        fi = ticker.fast_info
        
        last = getattr(fi, "last_price", None)
        prev = getattr(fi, "previous_close", None)
        
        # Fallback to .info or 1d history if fast_info has no price
        currency = getattr(fi, "currency", "IDR" if market == "IDX" else "USD")
        name = code
        pe = None
        pbv = None
        market_cap = None
        
        if last is None:
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            else:
                info = ticker.info
                last = info.get("regularMarketPrice") or info.get("currentPrice")
                prev = info.get("regularMarketPreviousClose")
                currency = info.get("currency", currency)
                name = info.get("shortName") or info.get("longName", code)
                pe = info.get("trailingPE")
                pbv = info.get("priceToBook")
                market_cap = info.get("marketCap")

        if last is None:
            # Check stale cache before raising
            stale = cache.get_stale(cache_key)
            if stale:
                return stale
            raise DataNotFoundError(f"{market}:{code}", provider="yahoo", message=f"Harga tidak ditemukan untuk {yahoo_sym}")

        last = float(last)
        prev = float(prev) if prev else last
        change = last - prev
        change_pct = ((last / prev) - 1.0) * 100.0 if prev else 0.0

        res = {
            "symbol": f"{market}:{code}",
            "market": market,
            "code": code,
            "yahoo_ticker": yahoo_sym,
            "name": name,
            "price": round(last, 2 if last < 100 else 1 if last < 500 else 0 if market == "IDX" else 2),
            "prev_close": round(prev, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "currency": currency,
            "pe": round(pe, 2) if pe else None,
            "pbv": round(pbv, 2) if pbv else None,
            "market_cap": market_cap,
            "source": "Yahoo Finance",
            "as_of": now_utc_iso(),
            "market_status": mkt_status["status_label"],
            "is_open": mkt_status["is_open"],
            "delay_note": mkt_status["delay_note"],
            "stale": False
        }

        # Cache TTL: 45s during market open, 10 minutes when closed
        ttl = 45 if mkt_status["is_open"] else 600
        cache.set(cache_key, res, ttl_seconds=ttl)
        return res

    except Exception as e:
        stale = cache.get_stale(cache_key)
        if stale:
            return stale
        raise ProviderError("yahoo", f"Gagal mengambil kuotasi {market}:{code}: {str(e)}")

def get_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    results = []
    for s in symbols:
        try:
            m, c = resolve_symbol(s)
            q = get_quote(m, c)
            results.append(q)
        except Exception:
            continue
    return results

def get_history(market: str, code: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    market = market.upper()
    code = code.upper()
    cache_key = f"hist:{market}:{code}:{period}:{interval}"
    
    # Check cache
    cached_json = cache.get(cache_key)
    if cached_json:
        df = pd.DataFrame.from_dict(cached_json, orient="index")
        df.index = pd.to_datetime(df.index)
        return df

    yahoo_sym = to_yahoo_ticker(market, code)
    try:
        t = yf.Ticker(yahoo_sym)
        df = t.history(period=period, interval=interval)
        if df.empty:
            raise DataNotFoundError(f"{market}:{code}", provider="yahoo", message=f"Histori data kosong untuk {yahoo_sym}")
        
        # Keep clean OHLCV
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df.dropna(inplace=True)

        # Cache for 6 hours
        records = df.to_dict(orient="index")
        # Format keys to string for JSON serialization
        str_records = {k.isoformat() if hasattr(k, "isoformat") else str(k): v for k, v in records.items()}
        cache.set(cache_key, str_records, ttl_seconds=21600)
        return df
    except Exception as e:
        raise ProviderError("yahoo", f"Gagal mengambil data histori {market}:{code}: {str(e)}")

def get_fundamentals(market: str, code: str) -> Dict[str, Any]:
    market = market.upper()
    code = code.upper()
    cache_key = f"fund:{market}:{code}"
    
    cached = cache.get(cache_key)
    if cached:
        return cached

    yahoo_sym = to_yahoo_ticker(market, code)
    try:
        ticker = yf.Ticker(yahoo_sym)
        info = ticker.info or {}
        
        res = {
            "symbol": f"{market}:{code}",
            "market": market,
            "code": code,
            "name": info.get("shortName") or info.get("longName", code),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "currency": info.get("currency"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "ratios": {
                "pe": round(info["trailingPE"], 2) if info.get("trailingPE") else None,
                "forward_pe": round(info["forwardPE"], 2) if info.get("forwardPE") else None,
                "pbv": round(info["priceToBook"], 2) if info.get("priceToBook") else None,
                "roe": round(info["returnOnEquity"] * 100, 2) if info.get("returnOnEquity") else None,
                "roa": round(info["returnOnAssets"] * 100, 2) if info.get("returnOnAssets") else None,
                "der": round(info["debtToEquity"], 2) if info.get("debtToEquity") else None,
                "eps": round(info["trailingEps"], 2) if info.get("trailingEps") else None,
                "dividend_yield": round(info["dividendYield"] * 100, 2) if info.get("dividendYield") else None,
                "profit_margin": round(info["profitMargins"] * 100, 2) if info.get("profitMargins") else None,
                "operating_margin": round(info["operatingMargins"] * 100, 2) if info.get("operatingMargins") else None,
                "revenue_growth": round(info["revenueGrowth"] * 100, 2) if info.get("revenueGrowth") else None,
                "current_ratio": round(info["currentRatio"], 2) if info.get("currentRatio") else None,
                "quick_ratio": round(info["quickRatio"], 2) if info.get("quickRatio") else None,
            },
            "source": "Yahoo Finance",
            "as_of": now_utc_iso()
        }
        
        # Cache for 24 hours
        cache.set(cache_key, res, ttl_seconds=86400)
        return res
    except Exception as e:
        stale = cache.get_stale(cache_key)
        if stale:
            return stale
        raise ProviderError("yahoo", f"Gagal mengambil fundamental {market}:{code}: {str(e)}")

def get_market_overview() -> Dict[str, Any]:
    cache_key = "market_overview"
    cached = cache.get(cache_key)
    if cached:
        return cached

    items = [
        {"name": "IHSG", "symbol": "^JKSE", "market": "IDX"},
        {"name": "LQ45", "symbol": "^JKLQ45", "market": "IDX"},
        {"name": "STI (Singapura)", "symbol": "^STI", "market": "SGX"},
        {"name": "S&P 500", "symbol": "^GSPC", "market": "US"},
        {"name": "Nasdaq", "symbol": "^IXIC", "market": "US"},
        {"name": "SSE Composite", "symbol": "000001.SS", "market": "SSE"},
        {"name": "USD/IDR", "symbol": "USDIDR=X", "market": "US"},
        {"name": "VIX", "symbol": "^VIX", "market": "US"},
        {"name": "Minyak Mentah (WTI)", "symbol": "CL=F", "market": "US"},
        {"name": "Emas (Gold)", "symbol": "GC=F", "market": "US"},
    ]

    overview_list = []
    for it in items:
        try:
            q = get_quote(it["market"], it["symbol"])
            overview_list.append({
                "name": it["name"],
                "symbol": it["symbol"],
                "price": q["price"],
                "change": q["change"],
                "change_pct": q["change_pct"],
                "currency": q["currency"],
                "as_of": q["as_of"]
            })
        except Exception:
            continue

    res = {
        "indices": overview_list,
        "as_of": now_utc_iso(),
        "source": "Yahoo Finance"
    }
    cache.set(cache_key, res, ttl_seconds=120)
    return res
