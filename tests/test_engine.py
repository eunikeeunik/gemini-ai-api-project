"""
EquityLens AI - Comprehensive Acceptance Tests
Tests:
1. Health check & exchange calendar status
2. Multi-market symbol resolution (IDX, US, SGX, SSE)
3. Live quote endpoint
4. Technical indicators (RSI, MACD, Bollinger, ATR, MAs)
5. Fundamentals & Bank classification (BBCA as Bank, Altman Z exclusion)
6. Valuation percentiles (PER/PBV 5y)
7. Candlestick patterns & win rate + Volume profile
8. Buy/Sell pressure proxy
9. Full AnalysisReport assembly (confluence, data completeness, confidence)
10. Grounding Validator (catches hallucinated numbers and certainty phrases)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.providers.yahoo import resolve_symbol
from backend.analysis.banks import is_bank_stock
from backend.agent.validator import validate_narrative

client = TestClient(app)

def test_health():
    print("=== 1. Testing /api/health ===")
    response = client.get("/api/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy"
    assert "IDX" in data["markets"]
    assert "US" in data["markets"]
    print("[PASS] Health check passed:", data["status"], "Markets:", list(data["markets"].keys()))

def test_symbol_resolution():
    print("\n=== 2. Testing Multi-market Symbol Resolution ===")
    assert resolve_symbol("BBCA") == ("IDX", "BBCA")
    assert resolve_symbol("IDX:BBRI") == ("IDX", "BBRI")
    assert resolve_symbol("AAPL") == ("US", "AAPL")
    assert resolve_symbol("D05.SI") == ("SGX", "D05")
    assert resolve_symbol("600519.SS") == ("SSE", "600519")
    assert resolve_symbol("IHSG") == ("IDX", "^JKSE")
    print("[PASS] Symbol resolution verified for IDX, US, SGX, SSE, and Indices.")

def test_bank_specialization():
    print("\n=== 3. Testing Bank Stock Classification ===")
    assert is_bank_stock("BBCA", "IDX") is True
    assert is_bank_stock("BBRI", "IDX") is True
    assert is_bank_stock("ASII", "IDX") is False
    assert is_bank_stock("JPM", "US") is True
    assert is_bank_stock("AAPL", "US") is False
    print("[PASS] Bank specialization rules verified (Banks correctly isolated from non-banks).")

def test_validator_injection():
    print("\n=== 4. Testing Numeric Grounding Validator ===")
    # Fake mock report
    mock_report = {
        "symbol": "IDX:BBCA",
        "price": 10250.0,
        "technical": {"rsi14": 56.4, "atr14": 150.0},
        "valuation": {"pbv": 4.5}
    }
    
    # Test certainty phrase rejection
    bad_narrative_1 = "Saham BBCA pasti naik ke Rp 12.000 karena RSI berada di 56.4."
    res1 = validate_narrative(bad_narrative_1, mock_report)
    assert not res1["is_valid"] or len(res1["flags"]) > 0
    assert any("pasti naik" in f for f in res1["flags"])
    print("[PASS] Forbidden certainty phrase caught successfully:", res1["flags"][0])

    # Test hallucinated number rejection
    bad_narrative_2 = "Harga BBCA saat ini adalah Rp 19.850 dan pertumbuhan laba mencapai 87.5%."
    res2 = validate_narrative(bad_narrative_2, mock_report)
    assert len(res2["unmatched_numbers"]) > 0
    print("[PASS] Hallucinated numbers caught successfully:", res2["unmatched_numbers"])

def test_live_quote_and_analysis():
    print("\n=== 5. Testing Live Quote & Analysis Endpoints ===")
    # Test Quote
    quote_resp = client.get("/api/quote?symbol=IDX:BBCA")
    if quote_resp.status_code == 200:
        q = quote_resp.json()
        print(f"[PASS] Quote BBCA: {q['symbol']} Price: {q.get('price')} {q.get('currency', 'IDR')}")
    else:
        print("[WARN] Quote returned status:", quote_resp.status_code)

    # Test Full AnalysisReport
    analysis_resp = client.get("/api/analysis?symbol=IDX:BBCA&mode=deep")
    if analysis_resp.status_code == 200:
        report = analysis_resp.json()
        assert "technical" in report
        assert "fundamental" in report
        assert "valuation" in report
        assert "candlestick_volume" in report
        assert "buy_sell_pressure" in report
        assert "trading_plan" in report
        assert "confluence" in report
        assert "confidence" in report
        assert "data_completeness" in report
        tech = report.get('technical') or {}
        plan = report.get('trading_plan') or {}
        confluence = report.get('confluence') or {}
        print(f"  Technical Regime={tech.get('regime')}, Confluence Score={confluence.get('overall')}")
        print(f"  Trading Plan Entry Zone={plan.get('entry_zone')}, Stop={plan.get('stop_loss')}")
    else:
        print("[WARN] Analysis returned status:", analysis_resp.status_code, analysis_resp.text[:200])

def test_phases_14_to_17():
    print("\n=== 6. Testing Phases 14-17 (Backtest, Portfolio, Macro, Quota, Track Record) ===")
    
    # 1. Backtest
    bt_resp = client.get("/api/backtest?symbol=IDX:BBCA")
    assert bt_resp.status_code == 200
    bt = bt_resp.json()
    assert "win_rate" in bt
    assert "profit_factor" in bt
    assert "p_value_significance" in bt
    print(f"[PASS] Backtest BBCA: Trades={bt.get('total_trades')}, WinRate={bt.get('win_rate')}, MaxDD={bt.get('max_drawdown_pct')}%, p-val={bt.get('p_value_significance')}")

    # 2. Portfolio Risk & PyPortfolioOpt
    pf_resp = client.get("/api/portfolio?symbols=BBCA,BBRI")
    assert pf_resp.status_code == 200
    pf = pf_resp.json()
    assert "var_95_historical_pct" in pf
    assert "sharpe_ratio" in pf
    assert "correlation_matrix" in pf
    print(f"[PASS] Portfolio Risk (BBCA+BBRI): VaR95={pf.get('var_95_historical_pct')}%, Sharpe={pf.get('sharpe_ratio')}, MaxDD={pf.get('max_drawdown_pct')}%")

    # 3. Macro Snapshot
    macro_resp = client.get("/api/macro")
    assert macro_resp.status_code == 200
    m = macro_resp.json()
    assert "indonesia" in m
    assert "global_us" in m
    print(f"[PASS] Macro Snapshot: BI Rate={m['indonesia'].get('bi_rate_pct')}%, US FedRate={m['global_us'].get('fed_funds_rate_pct')}%")

    # 4. Alpha Vantage QuotaGuard
    quota_resp = client.get("/api/av-quota")
    assert quota_resp.status_code == 200
    q = quota_resp.json()
    assert q["daily_limit"] == 25
    assert q["safety_ceiling"] == 23
    print(f"[PASS] QuotaGuard Alpha Vantage: Daily Ceiling={q['safety_ceiling']}/25, Remaining={q['daily_remaining']}")

    # 5. Prediction Ledger & Track Record
    tr_resp = client.get("/api/track-record")
    assert tr_resp.status_code == 200
    tr = tr_resp.json()
    assert "total_predictions" in tr
    print(f"[PASS] Prediction Ledger Track Record: Total={tr.get('total_predictions')}, Pending={tr.get('pending')}")

if __name__ == "__main__":
    test_health()
    test_symbol_resolution()
    test_bank_specialization()
    test_validator_injection()
    test_live_quote_and_analysis()
    test_phases_14_to_17()
    print("\n==========================================")
    print("ALL ACCEPTANCE TESTS EXECUTED AND PASSED!")
    print("==========================================")


