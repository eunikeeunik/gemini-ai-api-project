"""
EquityLens AI - Numeric Grounding Validator (Fase 13 - Spec 13.3)
Validates that Gemini's narrative only cites calculated figures from AnalysisReport,
catches hallucinations, and rejects forbidden certainty claims.
"""
import re
from typing import Dict, Any, List, Set, Tuple

# Forbidden certainty phrases that violate investment advisory ethics / risk standards
FORBIDDEN_CERTAINTY_PATTERNS = [
    r"\bpasti\s+naik\b",
    r"\bpasti\s+turun\b",
    r"\bpasti\s+untung\b",
    r"\bpasti\s+cuan\b",
    r"\bdijamin\b",
    r"\bgaransi\b",
    r"\b100%\s*(pasti|akurat|untung|cuan)\b",
    r"\btanpa\s+risiko\b",
    r"\btidak\s+mungkin\s+rugi\b",
    r"\b guaranteed\b",
    r"\brisk[-\s]?free\b",
]

# Standard technical periods and common numbers to ignore during grounding check
STANDARD_EXEMPTIONS: Set[float] = {
    0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 20.0, 26.0, 30.0, 50.0, 100.0, 200.0,
    2020.0, 2021.0, 2022.0, 2023.0, 2024.0, 2025.0, 2026.0, 2027.0
}


def extract_numbers_from_dict(data: Any) -> List[float]:
    """Recursively collects all numerical values from an AnalysisReport or dict."""
    nums = []
    if isinstance(data, dict):
        for v in data.values():
            nums.extend(extract_numbers_from_dict(v))
    elif isinstance(data, list):
        for item in data:
            nums.extend(extract_numbers_from_dict(item))
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        nums.append(float(data))
    return nums


def extract_numbers_from_text(text: str) -> List[Tuple[float, str]]:
    """
    Extracts numerical candidates from textual narrative.
    Returns list of (float_value, matched_raw_string).
    Handles Indonesian number format (Rp 10.500, 12,5%, etc.) and standard formats.
    """
    candidates = []
    
    # 1. Percentages: e.g. 12.5%, 12,5%, -3.2%
    for m in re.finditer(r"([+-]?\d+(?:[.,]\d+)?)\s*%", text):
        raw = m.group(1).replace(",", ".")
        try:
            val = float(raw)
            candidates.append((val, m.group(0)))
            # Also append decimal form e.g. 12.5% -> 0.125
            candidates.append((round(val / 100.0, 4), m.group(0)))
        except ValueError:
            pass

    # 2. Currency amounts e.g. Rp 10.500, Rp10,500, $150.25
    for m in re.finditer(r"(?:Rp|\$)\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]+)?)", text, re.IGNORECASE):
        clean = m.group(1)
        # Determine thousand separator vs decimal
        if "." in clean and "," in clean:
            # e.g. 10.500,50 -> 10500.50
            clean = clean.replace(".", "").replace(",", ".")
        elif "." in clean and len(clean.split(".")[-1]) == 3:
            # e.g. 10.500 -> 10500
            clean = clean.replace(".", "")
        elif "," in clean and len(clean.split(",")[-1]) == 3:
            # e.g. 10,500 -> 10500
            clean = clean.replace(",", "")
        else:
            clean = clean.replace(",", ".")
        try:
            candidates.append((float(clean), m.group(0)))
        except ValueError:
            pass

    # 3. Floating numbers / ratios e.g. 1.85x, 0.45
    for m in re.finditer(r"\b([0-9]+(?:[.,][0-9]+)?)\s*(?:x|kali)?\b", text):
        raw = m.group(1).replace(",", ".")
        try:
            val = float(raw)
            candidates.append((val, m.group(0)))
        except ValueError:
            pass

    return candidates


def is_number_grounded(target: float, ground_truth: List[float], rel_tol: float = 0.03, abs_tol: float = 1.0) -> bool:
    """
    Checks if a target number matches any number in the ground truth set
    within a relative or absolute tolerance.
    """
    if target in STANDARD_EXEMPTIONS:
        return True
    
    for gt in ground_truth:
        # Exact match
        if gt == target:
            return True
        # Absolute tolerance for small ratios
        if abs(gt - target) <= (0.05 if abs(gt) < 10 else abs_tol):
            return True
        # Relative tolerance for stock prices and percentages
        if gt != 0:
            if abs(gt - target) / abs(gt) <= rel_tol:
                return True
        # Check percentage representation (e.g. 0.05 vs 5.0)
        if gt != 0 and abs((gt * 100) - target) <= (1.0 if abs(target) > 5 else 0.1):
            return True
        if target != 0 and abs((target * 100) - gt) <= (1.0 if abs(gt) > 5 else 0.1):
            return True

    return False


def validate_narrative(narrative: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a generated LLM narrative against an AnalysisReport.
    Checks:
    1. Forbidden certainty claims.
    2. Grounding of numbers extracted from the text.
    """
    flags: List[str] = []
    forbidden_found: List[str] = []
    
    # 1. Check forbidden certainty patterns
    for pat in FORBIDDEN_CERTAINTY_PATTERNS:
        matches = re.findall(pat, narrative, re.IGNORECASE)
        if matches:
            forbidden_found.extend(matches)
            flags.append(f"Ditemukan klaim kepastian terlarang: '{', '.join(matches)}'. Investasi selalu mengandung risiko.")

    # 2. Extract ground truth numbers
    ground_truth = extract_numbers_from_dict(report_data)
    
    # 3. Extract text numbers
    text_numbers = extract_numbers_from_text(narrative)
    unmatched: List[Tuple[float, str]] = []
    
    for num, raw_str in text_numbers:
        if not is_number_grounded(num, ground_truth):
            # Verify if it's not a common exemption
            if num not in STANDARD_EXEMPTIONS:
                unmatched.append((num, raw_str))

    # De-duplicate unmatched
    unique_unmatched = []
    seen = set()
    for num, raw in unmatched:
        if raw not in seen:
            seen.add(raw)
            unique_unmatched.append(raw)

    if unique_unmatched:
        flags.append(f"Angka tidak terverifikasi dalam AnalysisReport: {', '.join(unique_unmatched[:8])}")

    is_valid = len(forbidden_found) == 0 and len(unique_unmatched) <= 2  # Allow up to 2 benign non-grounded numbers

    return {
        "is_valid": is_valid,
        "flags": flags,
        "forbidden_phrases": forbidden_found,
        "unmatched_numbers": unique_unmatched,
        "total_numbers_checked": len(text_numbers),
        "ground_truth_count": len(ground_truth)
    }
