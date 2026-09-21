"""
EquityLens AI - Valuation Module (Fase 9)
Calculates PER/PBV percentile valuation bands, DCF with WACC sensitivity matrix,
and Margin of Safety.
"""
from typing import Dict, Any, List, Optional
import numpy as np

def compute_dcf_sensitivity(
    fcf_current: float,
    shares_out: float,
    current_price: float,
    wacc_rates: Optional[List[float]] = None,
    growth_rates: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Computes a DCF fair value range with a sensitivity matrix of WACC vs Terminal Growth.
    """
    if fcf_current <= 0 or shares_out <= 0:
        return {
            "fair_value_range": None,
            "sensitivity_matrix": [],
            "note": "FCF negatif atau data saham beredar tidak memadai untuk kalkulasi DCF"
        }

    wacc_rates = wacc_rates or [0.09, 0.10, 0.11, 0.12]
    growth_rates = growth_rates or [0.02, 0.03, 0.04, 0.05]

    matrix = []
    fair_values = []

    for w in wacc_rates:
        row = {"wacc_pct": round(w * 100, 1), "values": []}
        for g in growth_rates:
            if w <= g:
                fv_per_share = 0.0
            else:
                # 5-year forecast at g + terminal value at g
                pv_fcf = 0.0
                fcf = fcf_current
                for year in range(1, 6):
                    fcf = fcf * (1 + g + 0.02)  # short term higher growth
                    pv_fcf += fcf / ((1 + w) ** year)
                
                terminal_val = (fcf * (1 + g)) / (w - g)
                pv_terminal = terminal_val / ((1 + w) ** 5)
                total_ev = pv_fcf + pv_terminal
                fv_per_share = total_ev / shares_out
            
            fair_values.append(fv_per_share)
            row["values"].append({
                "terminal_growth_pct": round(g * 100, 1),
                "fair_value": round(float(fv_per_share), 2)
            })
        matrix.append(row)

    valid_fvs = [fv for fv in fair_values if fv > 0]
    if valid_fvs:
        min_fv = round(float(np.percentile(valid_fvs, 20)), 2)
        base_fv = round(float(np.median(valid_fvs)), 2)
        max_fv = round(float(np.percentile(valid_fvs, 80)), 2)
        
        mos_pct = ((base_fv - current_price) / base_fv) * 100.0 if base_fv > 0 else 0.0
        verdict = "Undervalued (Margin of Safety Tersedia)" if mos_pct > 15 else "Overvalued (Premium)" if mos_pct < -15 else "Fairly Valued"

        return {
            "fair_value_range": {
                "bearish_min": min_fv,
                "base_case": base_fv,
                "bullish_max": max_fv,
            },
            "margin_of_safety_pct": round(mos_pct, 1),
            "verdict": verdict,
            "sensitivity_matrix": matrix
        }

    return {"fair_value_range": None, "sensitivity_matrix": []}

def analyze_valuation(current_price: float, pe: Optional[float], pbv: Optional[float], market_cap: Optional[float]) -> Dict[str, Any]:
    """Generates comprehensive valuation assessment and PBV/PER percentiles"""
    # Heuristic historical percentile bands
    pe_percentile = 0.50
    pbv_percentile = 0.50

    if pe:
        if pe < 10.0:
            pe_percentile = 0.20
        elif pe < 15.0:
            pe_percentile = 0.40
        elif pe < 22.0:
            pe_percentile = 0.65
        else:
            pe_percentile = 0.85

    if pbv:
        if pbv < 1.0:
            pbv_percentile = 0.15
        elif pbv < 2.0:
            pbv_percentile = 0.45
        elif pbv < 4.0:
            pbv_percentile = 0.70
        else:
            pbv_percentile = 0.90

    # Valuation rating
    avg_perc = (pe_percentile + pbv_percentile) / 2.0
    if avg_perc <= 0.30:
        val_status = "Undervalued (Murah Relatif terhadap Riwayat)"
        score = 0.4
    elif avg_perc >= 0.75:
        val_status = "Overvalued (Mahal Relatif terhadap Riwayat)"
        score = -0.4
    else:
        val_status = "Fairly Valued (Wajar)"
        score = 0.0

    return {
        "score": round(score, 2),
        "status": val_status,
        "current_pe": pe,
        "pe_percentile_5y": pe_percentile,
        "current_pbv": pbv,
        "pbv_percentile_5y": pbv_percentile,
        "graham_number": round(np.sqrt(22.5 * (pe or 15) * (pbv or 1.5) * (current_price / (pbv or 1.5))), 2) if pe and pbv and pe > 0 and pbv > 0 else None
    }
