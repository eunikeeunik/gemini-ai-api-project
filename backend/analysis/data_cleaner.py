"""
EquityLens AI - Data Cleaner & IDX Rules Engine (Fase 7)
Handles tick size rounding, lot sizing, illiquid stock warnings,
zero-volume days, ARA/ARB limits, and data completeness scoring.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional

IDX_LOT_SIZE = 100
MIN_DAILY_TURNOVER_IDR = 1_000_000_000.0  # Rp 1 Miliar threshold

def get_idx_tick_size(price: float) -> int:
    """Returns the valid price fraction (tick size) on the Indonesia Stock Exchange"""
    if price < 200:
        return 1
    elif price < 500:
        return 2
    elif price < 2000:
        return 5
    elif price < 5000:
        return 10
    else:
        return 25

def round_to_idx_tick(price: float, direction: str = "nearest") -> float:
    """Rounds a price to the nearest valid IDX tick size"""
    if price <= 0:
        return 0.0
    tick = get_idx_tick_size(price)
    if direction == "up":
        return float(np.ceil(price / tick) * tick)
    elif direction == "down":
        return float(np.floor(price / tick) * tick)
    else:
        return float(np.round(price / tick) * tick)

def shares_to_lots(shares: int) -> int:
    """Converts share count to standard lots (1 lot = 100 shares)"""
    return max(1, shares // IDX_LOT_SIZE)

def lots_to_shares(lots: int) -> int:
    return lots * IDX_LOT_SIZE

def calculate_lot_shares(raw_shares: int) -> int:
    """Rounds raw share count down to the nearest valid lot size (multiples of 100)."""
    return lots_to_shares(shares_to_lots(raw_shares))

def clean_ohlcv_dataframe(df: pd.DataFrame, market: str = "IDX") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans OHLCV dataframe:
    - Removes zero volume / trading halt days
    - Flags ARA / ARB days
    - Checks liquidity
    """
    if df.empty:
        return df, {"is_liquid": False, "avg_turnover": 0.0, "warnings": ["Data histori kosong"]}

    clean_df = df.copy()
    
    # 1. Filter zero volume
    initial_rows = len(clean_df)
    clean_df = clean_df[clean_df["Volume"] > 0].copy()
    dropped_zero_vol = initial_rows - len(clean_df)

    # 2. Check Liquidity (last 20 bars average turnover)
    recent_20 = clean_df.tail(20)
    avg_turnover = float((recent_20["Close"] * recent_20["Volume"]).mean())
    is_liquid = True
    warnings = []

    if market == "IDX":
        if avg_turnover < MIN_DAILY_TURNOVER_IDR:
            is_liquid = False
            warnings.append(
                f"Saham tidak likuid: Rata-rata transaksi harian hanya Rp {avg_turnover/1e6:.1f} Juta (di bawah Rp 1 Miliar). "
                "Sinyal teknikal berpotensi kurang andal dan risiko slippage tinggi."
            )

    # 3. Detect ARA / ARB (for IDX: ~20-35% or 7-15% limit hits depending on price bracket)
    if market == "IDX" and len(clean_df) > 1:
        pct_chg = clean_df["Close"].pct_change()
        clean_df["is_ara"] = pct_chg >= 0.19
        clean_df["is_arb"] = pct_chg <= -0.14
    else:
        clean_df["is_ara"] = False
        clean_df["is_arb"] = False

    meta = {
        "is_liquid": is_liquid,
        "avg_turnover_idr": avg_turnover,
        "dropped_zero_vol_days": dropped_zero_vol,
        "warnings": warnings
    }
    return clean_df, meta

def calculate_data_completeness(
    has_quote: bool,
    has_history: bool,
    has_fundamentals: bool,
    has_technicals: bool,
    has_news: bool,
    has_bank_metrics: Optional[bool] = None,
    is_bank: bool = False,
    has_broker_flow: bool = False
) -> Dict[str, Any]:
    """
    Computes data completeness score (0.0 to 1.0) and lists missing items.
    """
    items = [
        ("quote", has_quote, 0.20),
        ("history", has_history, 0.25),
        ("fundamentals", has_fundamentals, 0.20),
        ("technicals", has_technicals, 0.15),
        ("news", has_news, 0.10),
    ]
    
    missing = []
    score = 0.0
    
    for name, available, weight in items:
        if available:
            score += weight
        else:
            missing.append(name)

    if not has_broker_flow:
        missing.append("broker_flow (data bandarmologi berbayar)")

    if is_bank:
        if has_bank_metrics:
            score = score * 0.9 + 0.10
        else:
            missing.append("bank_metrics (NIM/NPL/CAR)")
            score = score * 0.9

    return {
        "score": round(min(1.0, max(0.0, score)), 2),
        "missing": missing
    }
