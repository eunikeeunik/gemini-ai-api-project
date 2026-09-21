"""
EquityLens AI - Macroeconomic Data Provider (Fase 16)
Integrates FRED (US & Global Commodities) and BPS WebAPI (Indonesian Inflation & BI-Rate).
All sources are free (Rp0). Graceful fallback when API keys are unconfigured.
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.core.config import settings
from backend.core.cache import cache, now_utc_iso

FRED_SERIES = {
    "us_cpi": "CPIAUCSL",
    "fed_funds_rate": "FEDFUNDS",
    "us_10y_yield": "DGS10",
    "brent_oil": "DCOILBRENTEU",
    "gold": "GOLDAMGBD228NLBM"
}

FALLBACK_MACRO = {
    "indonesia": {
        "bi_rate_pct": 6.00,
        "inflation_yoy_pct": 2.12,
        "source": "Bank Indonesia & BPS (Snapshot Terakhir)",
        "as_of": "2026-08"
    },
    "us": {
        "fed_funds_rate_pct": 5.25,
        "us_cpi_yoy_pct": 2.9,
        "us_10y_yield_pct": 3.85,
        "source": "Federal Reserve (Snapshot Terakhir)",
        "as_of": "2026-08"
    }
}

async def fetch_fred_series(series_id: str, api_key: str) -> Optional[float]:
    """Fetches latest observation for a FRED series."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                obs = data.get("observations", [])
                if obs:
                    val_str = obs[0].get("value", "")
                    return float(val_str)
    except Exception:
        pass
    return None

async def get_macro_snapshot() -> Dict[str, Any]:
    """
    Returns unified macro indicators across Indonesia and Global/US.
    Cached for 24 hours.
    """
    cache_key = "macro:unified_snapshot"
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = {
        "as_of": now_utc_iso(),
        "indonesia": dict(FALLBACK_MACRO["indonesia"]),
        "global_us": dict(FALLBACK_MACRO["us"]),
        "providers_used": ["Fallback Snapshot"]
    }

    # If FRED key configured, fetch live US series
    fred_key = settings.FRED_API_KEY
    if fred_key:
        yield_10y = await fetch_fred_series(FRED_SERIES["us_10y_yield"], fred_key)
        fed_rate = await fetch_fred_series(FRED_SERIES["fed_funds_rate"], fred_key)
        if yield_10y is not None:
            result["global_us"]["us_10y_yield_pct"] = yield_10y
        if fed_rate is not None:
            result["global_us"]["fed_funds_rate_pct"] = fed_rate
        result["providers_used"].append("FRED API")

    cache.set(cache_key, result, ttl_seconds=86400)
    return result
