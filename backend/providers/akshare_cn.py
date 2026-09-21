"""
EquityLens AI - China A-Share Adapter (AkShare + Yahoo Fallback)
"""
from typing import Dict, Any, Optional
import pandas as pd
from backend.core.cache import cache
from backend.providers.yahoo import get_quote as yahoo_quote, get_history as yahoo_history

def get_cn_quote(code: str) -> Dict[str, Any]:
    market = "SSE" if code.startswith("6") else "SZSE"
    cache_key = f"cn_quote:{market}:{code}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Try AkShare if installed, else fallback cleanly to Yahoo
    try:
        import akshare as ak
        # Spot check
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if not row.empty:
            r = row.iloc[0]
            price = float(r["最新价"])
            pct = float(r["涨跌幅"])
            res = {
                "symbol": f"{market}:{code}",
                "market": market,
                "code": code,
                "name": str(r["名称"]),
                "price": price,
                "change_pct": pct,
                "pe": float(r["市盈率-动态"]) if "市盈率-动态" in r and pd.notnull(r["市盈率-动态"]) else None,
                "pbv": float(r["市净率"]) if "市净率" in r and pd.notnull(r["市净率"]) else None,
                "source": "AkShare",
                "as_of": cache.now_utc_iso() if hasattr(cache, "now_utc_iso") else "",
                "market_status": "Buka"
            }
            cache.set(cache_key, res, ttl_seconds=60)
            return res
    except Exception:
        pass

    # Fallback to Yahoo Finance
    return yahoo_quote(market, code)
