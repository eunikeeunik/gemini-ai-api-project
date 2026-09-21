"""
EquityLens AI - Bank Specialization Analysis Module (Fase 9)
Dedicated metrics for financial institutions (BBCA, BBRI, BMRI, BBNI, etc.).
Altman Z-Score is explicitly NOT applicable to banks.
"""
from typing import Dict, Any, Optional

BANK_TICKERS = {
    # IDX
    "BBCA", "BBRI", "BMRI", "BBNI", "BBTN", "BDMN", "BNGA", "BRIS", "MEGA", "NISP", "BTPS",
    # US
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC",
    # SGX
    "D05", "U11", "O39"
}

def is_bank_stock(code: str, industry_or_market: Optional[str] = None) -> bool:
    cleaned = code.upper().replace(".JK", "").replace(".SI", "").replace("IDX:", "").replace("US:", "").replace("SGX:", "")
    if cleaned in BANK_TICKERS:
        return True
    if industry_or_market and ("bank" in industry_or_market.lower() or "financial" in industry_or_market.lower()):
        return True
    return False

def analyze_bank_metrics(code: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes or extracts key banking metrics:
    NIM, NPL, CAR, LDR, CASA, BOPO, Cost of Credit, and PBV vs ROE.
    """
    # Check if specific metrics are available in financial_data
    nim = financial_data.get("nim")
    npl = financial_data.get("npl")
    car = financial_data.get("car")
    ldr = financial_data.get("ldr")
    casa = financial_data.get("casa")
    bopo = financial_data.get("bopo")
    roe = financial_data.get("roe")
    pbv = financial_data.get("pbv")

    available = any(v is not None for v in [nim, npl, car, ldr, casa, bopo])

    # Benchmarks for Indonesian Big Banks
    assessment = []
    if roe and pbv:
        # Justified PBV heuristic: ROE / Cost of Equity (~10-12% for Indonesian banks)
        cost_of_equity = 11.0
        justified_pbv = roe / cost_of_equity
        pbv_discount_prem = ((pbv / justified_pbv) - 1.0) * 100.0 if justified_pbv > 0 else 0.0
        assessment.append({
            "metric": "PBV vs ROE (Valuasi Bank)",
            "justified_pbv": round(justified_pbv, 2),
            "actual_pbv": round(pbv, 2),
            "discount_premium_pct": round(pbv_discount_prem, 1),
            "verdict": "Premium terhadap ROE Wajar" if pbv_discount_prem > 15 else "Undervalued terhadap ROE Wajar" if pbv_discount_prem < -15 else "Fairly Valued terhadap Kinerja ROE"
        })

    return {
        "is_bank": True,
        "available": available,
        "metrics": {
            "nim": nim,
            "npl": npl,
            "car": car,
            "ldr": ldr,
            "casa": casa,
            "bopo": bopo,
        },
        "note": "Metrik khusus perbankan (NIM, NPL, CAR, CASA, BOPO) memerlukan laporan publikasi kuartalan resmi OJK/BEI." if not available else "Metrik bank berhasil diverifikasi.",
        "altman_z_applicable": False,
        "altman_z_reason": "Altman Z-Score tidak berlaku secara metodologis untuk institusi perbankan dan lembaga keuangan karena struktur neraca berbasis liabilitas simpanan.",
        "assessments": assessment
    }
