"""
EquityLens AI - Trading Plan Generator (Fase 12)
Deterministic trading plan: entry zone, stop loss (ATR-based), targets,
R:R ratio, position sizing in lots. All prices rounded to IDX tick size.
"""
import numpy as np
from typing import Dict, Any, Optional
from backend.analysis.data_cleaner import round_to_idx_tick, shares_to_lots, lots_to_shares, IDX_LOT_SIZE

def generate_trading_plan(
    current_price: float,
    atr: float,
    support_levels: list,
    resistance_levels: list,
    market: str = "IDX",
    capital: float = 100_000_000.0,
    risk_pct: float = 0.01,
    horizon: str = "swing"
) -> Dict[str, Any]:
    """
    Generates a deterministic trading plan with all calculations in code.
    Gemini narrates this result, never computes it.
    """
    is_idx = market.upper() == "IDX"
    
    # Entry Zone: pullback to nearest support or current price area
    if support_levels:
        entry_base = max(s for s in support_levels if s < current_price * 0.99) if any(s < current_price * 0.99 for s in support_levels) else current_price * 0.98
    else:
        entry_base = current_price * 0.98

    entry_low = entry_base
    entry_high = current_price * 0.995

    # Stop Loss: 1.5x ATR below entry or below nearest support
    stop_atr = entry_low - (1.5 * atr)
    if support_levels:
        lowest_support = min(support_levels) if support_levels else entry_low * 0.95
        stop_structural = lowest_support * 0.99
        stop_loss = max(stop_atr, stop_structural)  # Use whichever is tighter but logical
    else:
        stop_loss = stop_atr

    # Targets: 1.5R, 2R, 3R multiples
    risk_per_share = entry_low - stop_loss
    if risk_per_share <= 0:
        risk_per_share = atr * 0.5  # Fallback

    target_1 = entry_low + (1.5 * risk_per_share)
    target_2 = entry_low + (2.0 * risk_per_share)
    target_3 = entry_low + (3.0 * risk_per_share)

    # Use resistance levels as reality check
    if resistance_levels:
        nearest_resistance = min(r for r in resistance_levels) if resistance_levels else target_2
        if target_1 > nearest_resistance * 1.05:
            target_1 = nearest_resistance

    # Round to IDX tick size
    if is_idx:
        entry_low = round_to_idx_tick(entry_low, "down")
        entry_high = round_to_idx_tick(entry_high, "up")
        stop_loss = round_to_idx_tick(stop_loss, "down")
        target_1 = round_to_idx_tick(target_1, "up")
        target_2 = round_to_idx_tick(target_2, "up")
        target_3 = round_to_idx_tick(target_3, "up")
        risk_per_share = entry_low - stop_loss

    # Risk:Reward ratio
    reward_1 = target_1 - entry_low
    rr_ratio = round(reward_1 / risk_per_share, 2) if risk_per_share > 0 else 0.0
    rr_warning = rr_ratio < 1.5

    # Position sizing
    risk_amount = capital * risk_pct
    if risk_per_share > 0:
        max_shares = int(risk_amount / risk_per_share)
    else:
        max_shares = 0
    
    if is_idx:
        lots = shares_to_lots(max_shares)
        shares = lots_to_shares(lots)
    else:
        lots = max_shares
        shares = max_shares

    total_cost = shares * entry_low
    max_loss = shares * risk_per_share

    return {
        "horizon": horizon,
        "entry_zone": {
            "low": round(float(entry_low), 2),
            "high": round(float(entry_high), 2),
        },
        "stop_loss": round(float(stop_loss), 2),
        "targets": {
            "tp1_1_5R": round(float(target_1), 2),
            "tp2_2R": round(float(target_2), 2),
            "tp3_3R": round(float(target_3), 2),
        },
        "risk_per_share": round(float(risk_per_share), 2),
        "risk_reward_ratio": rr_ratio,
        "rr_warning": "⚠️ Risk:Reward di bawah 1.5, rencana ini kurang ideal" if rr_warning else None,
        "position_size": {
            "capital": capital,
            "risk_pct": risk_pct * 100,
            "max_risk_amount": round(risk_amount, 0),
            "shares": shares,
            "lots": lots if is_idx else None,
            "total_cost": round(total_cost, 0),
            "max_loss": round(max_loss, 0),
        },
        "invalidation": f"Close di bawah {round(float(stop_loss), 0)} membatalkan skenario bullish",
        "disclaimer": "Trading plan ini adalah ILUSTRASI EDUKASI berdasarkan data yang tersedia, bukan rekomendasi investasi personal.",
        "atr_used": round(float(atr), 2),
    }
