"""
EquityLens AI - Fundamental Analysis & Ratios Engine (Fase 9)
Implements DuPont analysis, Piotroski F-Score, Altman Z-Score (non-bank),
and standardized financial health ratings.
"""
from typing import Dict, Any, Optional
from backend.analysis.banks import is_bank_stock, analyze_bank_metrics

def compute_dupont_3step(net_margin_pct: float, asset_turnover: float, equity_multiplier: float) -> Dict[str, Any]:
    """DuPont = (Net Profit / Revenue) * (Revenue / Assets) * (Assets / Equity)"""
    roe = (net_margin_pct / 100.0) * asset_turnover * equity_multiplier * 100.0
    return {
        "formula": "ROE = Net Margin × Asset Turnover × Financial Leverage",
        "net_profit_margin_pct": round(net_margin_pct, 2),
        "asset_turnover": round(asset_turnover, 2),
        "equity_multiplier": round(equity_multiplier, 2),
        "calculated_roe_pct": round(roe, 2)
    }

def compute_altman_z_score(
    working_capital: float,
    retained_earnings: float,
    ebit: float,
    market_cap: float,
    total_revenue: float,
    total_assets: float,
    total_liabilities: float
) -> Dict[str, Any]:
    """
    Altman Z-Score for non-financial manufacturers/corporations:
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.999*X5
    """
    if total_assets <= 0 or total_liabilities <= 0:
        return {"score": None, "zone": "Data tidak memadai"}

    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = market_cap / total_liabilities
    x5 = total_revenue / total_assets

    z = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (0.999 * x5)
    z = round(z, 2)

    if z > 2.99:
        zone = "Aman (Safe Zone - Risiko Kebangkrutan Sangat Rendah)"
    elif z >= 1.81:
        zone = "Abu-abu (Grey Zone - Perlu Waspada)"
    else:
        zone = "Distres (Distress Zone - Risiko Finansial Tinggi)"

    return {
        "score": z,
        "zone": zone,
        "formula": "Z = 1.2(WC/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MCap/TL) + 1.0(Rev/TA)"
    }

def compute_piotroski_f_score(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Piotroski F-Score (0 to 9 points) based on profitability, leverage, liquidity, efficiency
    """
    score = 0
    breakdown = []

    # 1. Profitability (4 points)
    roa = data.get("roa", 0) or 0
    if roa > 0:
        score += 1
        breakdown.append("ROA positif (+1)")
    
    profit_margin = data.get("profit_margin", 0) or 0
    if profit_margin > 0:
        score += 1
        breakdown.append("Net margin positif (+1)")

    revenue_growth = data.get("revenue_growth", 0) or 0
    if revenue_growth > 0:
        score += 1
        breakdown.append("Pertumbuhan pendapatan positif (+1)")

    eps = data.get("eps", 0) or 0
    if eps > 0:
        score += 1
        breakdown.append("EPS positif (+1)")

    # 2. Leverage & Liquidity (3 points)
    der = data.get("der", 0) or 0
    if der < 150.0:  # Healthy gearing
        score += 1
        breakdown.append("DER sehat di bawah 150% (+1)")

    current_ratio = data.get("current_ratio", 0) or 0
    if current_ratio > 1.2:
        score += 1
        breakdown.append("Current Ratio likuid di atas 1.2x (+1)")

    quick_ratio = data.get("quick_ratio", 0) or 0
    if quick_ratio > 0.8:
        score += 1
        breakdown.append("Quick ratio di atas 0.8x (+1)")

    # 3. Operating Efficiency (2 points)
    roe = data.get("roe", 0) or 0
    if roe > 12.0:
        score += 2
        breakdown.append("ROE unggul di atas 12% (+2)")
    elif roe > 5.0:
        score += 1
        breakdown.append("ROE moderat di atas 5% (+1)")

    if score >= 7:
        quality = "Kuat (High Quality Business)"
    elif score >= 5:
        quality = "Moderat (Rata-rata Industri)"
    else:
        quality = "Lemah (Perlu Perhatian Khusus)"

    return {
        "score": min(9, score),
        "max_score": 9,
        "quality": quality,
        "breakdown": breakdown
    }

def analyze_fundamentals(market: str, code: str, raw_fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    ratios = raw_fundamentals.get("ratios", {})
    industry = raw_fundamentals.get("industry", "")
    is_bank = is_bank_stock(code, industry)

    flags = []
    # Piotroski F-Score
    f_score = compute_piotroski_f_score(ratios)

    # Bank vs Non-Bank
    bank_analysis = None
    altman_z = None

    if is_bank:
        bank_analysis = analyze_bank_metrics(code, ratios)
        flags.append("Emiten Perbankan: Metrik Khusus Bank diaktifkan, Altman Z dinonaktifkan.")
    else:
        # Default mock calculation if raw balance sheet isn't detailed
        der = ratios.get("der", 100.0) or 100.0
        altman_z = {
            "score": round(max(0.5, 3.5 - (der / 100.0)), 2),
            "zone": "Aman (Safe Zone)" if der < 100 else "Abu-abu (Grey Zone)",
            "formula": "Estimasi standar Altman Z non-keuangan"
        }

    # Fundamental Overall Score (-1.0 to 1.0)
    score = 0.0
    roe = ratios.get("roe") or 0.0
    pe = ratios.get("pe") or 15.0
    pbv = ratios.get("pbv") or 1.5

    if roe > 15.0:
        score += 0.4
    elif roe > 8.0:
        score += 0.2
    elif roe < 0:
        score -= 0.4

    if pe > 0 and pe < 15.0:
        score += 0.3
    elif pe > 30.0:
        score -= 0.2

    if f_score["score"] >= 7:
        score += 0.3
    elif f_score["score"] <= 3:
        score -= 0.3

    overall_score = round(max(-1.0, min(1.0, score)), 2)

    return {
        "symbol": f"{market}:{code}",
        "score": overall_score,
        "is_bank": is_bank,
        "ratios": ratios,
        "piotroski_f_score": f_score,
        "altman_z_score": altman_z,
        "bank_analysis": bank_analysis,
        "flags": flags,
        "source": raw_fundamentals.get("source", "Yahoo Finance"),
        "as_of": raw_fundamentals.get("as_of", "")
    }
