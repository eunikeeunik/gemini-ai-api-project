"""
EquityLens AI - Confluence & Confidence Engine (Fase 12)
Aggregates scores from all analysis dimensions, detects conflicts,
and determines confidence level.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "config" / "weights.yaml"

def load_weights() -> Dict[str, Dict[str, float]]:
    try:
        with open(WEIGHTS_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return {
            "swing": {"technical": 0.35, "candlestick_volume": 0.20, "buy_sell_pressure": 0.15,
                      "sentiment": 0.10, "market_macro": 0.10, "fundamental": 0.05, "valuation": 0.05},
            "positional": {"technical": 0.20, "candlestick_volume": 0.10, "buy_sell_pressure": 0.10,
                           "sentiment": 0.10, "market_macro": 0.15, "fundamental": 0.20, "valuation": 0.15},
            "long_term": {"technical": 0.05, "candlestick_volume": 0.00, "buy_sell_pressure": 0.05,
                          "sentiment": 0.05, "market_macro": 0.10, "fundamental": 0.40, "valuation": 0.35},
        }

def calculate_confluence(
    scores: Dict[str, float],
    horizon: str = "swing",
    data_completeness_score: float = 1.0,
    has_stale_data: bool = False,
    model_edge: bool = False,
    is_illiquid: bool = False,
    is_new_ipo: bool = False
) -> Dict[str, Any]:
    """
    Calculates weighted confluence score and determines confidence level.
    """
    all_weights = load_weights()
    weights = all_weights.get(horizon, all_weights["swing"])

    weighted_sum = 0.0
    total_weight = 0.0
    dimension_details = []

    for dim, weight in weights.items():
        sc = scores.get(dim, 0.0)
        weighted_sum += sc * weight
        total_weight += weight
        dimension_details.append({
            "dimension": dim,
            "score": round(sc, 2),
            "weight": weight,
            "contribution": round(sc * weight, 3)
        })

    overall = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    # Detect conflicts: dimensions with opposite signs among high-weight ones
    conflicts = []
    high_weight_dims = [d for d in dimension_details if d["weight"] >= 0.15]
    for i, d1 in enumerate(high_weight_dims):
        for d2 in high_weight_dims[i+1:]:
            if (d1["score"] > 0.2 and d2["score"] < -0.2) or (d1["score"] < -0.2 and d2["score"] > 0.2):
                conflicts.append(f"{d1['dimension']} vs {d2['dimension']}")

    # Confidence determination
    confidence = "tinggi"
    downgrade_reasons = []

    if data_completeness_score < 0.70:
        confidence = "rendah"
        downgrade_reasons.append(f"Kelengkapan data hanya {data_completeness_score*100:.0f}%")
    elif data_completeness_score < 0.85:
        if confidence == "tinggi":
            confidence = "sedang"
        downgrade_reasons.append(f"Beberapa data tidak lengkap ({data_completeness_score*100:.0f}%)")

    if has_stale_data:
        if confidence == "tinggi":
            confidence = "sedang"
        downgrade_reasons.append("Ada data yang sudah usang (stale)")

    if len(conflicts) >= 2:
        if confidence == "tinggi":
            confidence = "sedang"
        downgrade_reasons.append(f"{len(conflicts)} dimensi utama saling bertentangan")

    if is_illiquid:
        if confidence != "rendah":
            confidence = "sedang" if confidence == "tinggi" else "rendah"
        downgrade_reasons.append("Saham tidak likuid, sinyal teknikal kurang andal")

    if is_new_ipo:
        if confidence != "rendah":
            confidence = "sedang" if confidence == "tinggi" else "rendah"
        downgrade_reasons.append("Saham baru IPO (< 1 tahun), data historis terbatas")

    return {
        "overall": overall,
        "verdict": "Bullish" if overall > 0.2 else "Bearish" if overall < -0.2 else "Netral",
        "dimensions": dimension_details,
        "conflicts": conflicts,
        "confidence": confidence,
        "confidence_reasons": downgrade_reasons,
        "horizon": horizon,
    }
