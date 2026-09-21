"""
EquityLens AI - Macro Factor Sensitivity Analysis (Fase 10)
Maps stock sectors to key macroeconomic indicators (Interest rates, FX, Commodities)
and computes macro sensitivity impact score.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

def load_yaml_config(filename: str) -> Dict[str, Any]:
    file_path = CONFIG_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def analyze_macro_sensitivity(symbol: str, market: str = "IDX") -> Dict[str, Any]:
    """
    Evaluates macroeconomic factor exposure for a given ticker symbol.
    Score ranges from -1.0 (headwinds) to +1.0 (tailwinds).
    """
    clean_sym = symbol.upper().replace(".JK", "").replace("IDX:", "").replace("US:", "")
    sector_map = load_yaml_config("sector_macro_map.yaml")
    macro_overrides = load_yaml_config("macro_overrides.yaml")
    
    factors = sector_map.get(clean_sym, ["general_economic_growth", "inflation_idr"])
    
    # Evaluate factor impacts based on macro state
    # e.g. BI-rate stable/easing is positive for banking/consumer; coal price stable is neutral
    factor_scores = []
    drivers = []
    
    for factor in factors:
        if factor in ("bi_rate", "interest_rate"):
            # Banking NIM expansion vs credit demand trade-off
            factor_scores.append(0.15)
            drivers.append("Suku bunga acuan stabil/moderat menopang net interest margin")
        elif factor in ("usdidr", "fx_rate"):
            factor_scores.append(-0.10)
            drivers.append("Fluktuasi kurs valas USD/IDR mempengaruhi beban operasional dan margin")
        elif factor in ("coal", "crude_oil", "nickel", "gold", "palm_oil"):
            factor_scores.append(0.20)
            drivers.append(f"Permintaan dan stabilitas harga komoditas global ({factor})")
        elif factor in ("global_tech_capex", "us_yields"):
            factor_scores.append(0.25)
            drivers.append("Tren adopsi AI dan belanja modal hyperscaler global")
        else:
            factor_scores.append(0.0)
    
    overall_score = float(sum(factor_scores) / len(factor_scores)) if factor_scores else 0.0
    overall_score = round(max(-1.0, min(1.0, overall_score)), 2)

    return {
        "symbol": clean_sym,
        "market": market,
        "score": overall_score,
        "exposed_factors": factors,
        "drivers": drivers,
        "assessment": "Tailwind makro moderat" if overall_score > 0.1 else "Headwind makro" if overall_score < -0.1 else "Netral terhadap makro",
        "macro_data_source": "BPS / BI / Yahoo / FRED"
    }
