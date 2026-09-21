"""
EquityLens AI - Trading Rule Backtest Engine (Fase 14)
Zero look-ahead bias: Signal generated at bar t close, filled at bar t+1 open.
Includes realistic fees, slippage, IDX tick sizes, and permutation significance tests.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from backend.analysis.data_cleaner import round_to_idx_tick, calculate_lot_shares

DEFAULT_COSTS = {
    "buy_fee_pct": 0.15,       # 0.15% broker buy fee
    "sell_fee_pct": 0.25,      # 0.25% broker sell fee + final tax
    "slippage_bps": 10,        # 10 bps slippage
}

class BacktestEngine:
    def __init__(self, costs: Optional[Dict[str, float]] = None):
        self.costs = costs or DEFAULT_COSTS

    def run_backtest(
        self,
        df: pd.DataFrame,
        market: str = "IDX",
        initial_capital: float = 100_000_000.0,
        risk_per_trade_pct: float = 0.01,
        rr_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        Executes causal backtest of EMA pullback / trend continuation rules.
        """
        if df is None or len(df) < 50:
            return {"error": "Histori harga tidak mencukupi untuk backtest (<50 bar)"}

        df = df.copy()
        close = df["Close"]
        open_p = df["Open"]
        high = df["High"]
        low = df["Low"]

        # 1. Causal Indicators (only rolling backwards)
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        # Signal at bar t close: Trend is up (ema20 > ema50) and pullback near ema20
        signal = (ema20 > ema50) & (close <= ema20 * 1.01) & (close >= ema20 * 0.98)

        trades = []
        in_trade = False
        entry_price = 0.0
        stop_price = 0.0
        target_price = 0.0
        shares = 0
        entry_idx = 0

        # Slippage adjustment
        slip_factor_buy = 1.0 + (self.costs["slippage_bps"] / 10000.0)
        slip_factor_sell = 1.0 - (self.costs["slippage_bps"] / 10000.0)
        buy_fee = self.costs["buy_fee_pct"] / 100.0
        sell_fee = self.costs["sell_fee_pct"] / 100.0

        for t in range(20, len(df) - 1):
            if not in_trade:
                # Check signal at bar t close -> enter at bar t+1 OPEN
                if signal.iloc[t]:
                    fill_open = float(open_p.iloc[t + 1])
                    current_atr = float(atr.iloc[t])
                    if current_atr <= 0:
                        continue

                    entry_price = fill_open * slip_factor_buy
                    if market == "IDX":
                        entry_price = round_to_idx_tick(entry_price)

                    stop_dist = max(1.5 * current_atr, entry_price * 0.02)
                    stop_price = entry_price - stop_dist
                    target_price = entry_price + (stop_dist * rr_ratio)

                    if market == "IDX":
                        stop_price = round_to_idx_tick(stop_price)
                        target_price = round_to_idx_tick(target_price)

                    # Position sizing
                    risk_amount = initial_capital * risk_per_trade_pct
                    risk_per_share = max(entry_price - stop_price, 1.0)
                    raw_shares = int(risk_amount / risk_per_share)
                    shares = calculate_lot_shares(raw_shares) if market == "IDX" else raw_shares
                    
                    if shares > 0:
                        in_trade = True
                        entry_idx = t + 1
            else:
                # Inside trade: evaluate exits on bar t
                bar_high = float(high.iloc[t])
                bar_low = float(low.iloc[t])
                bar_open = float(open_p.iloc[t])

                hit_stop = bar_low <= stop_price
                hit_target = bar_high >= target_price

                exit_price = None
                exit_reason = None

                # Conservative tie-breaking: if both hit in same bar, assume stop first
                if hit_stop:
                    # Gap down below stop handled by exiting at open if open < stop
                    exit_price = min(stop_price, bar_open) * slip_factor_sell
                    exit_reason = "STOP_LOSS"
                elif hit_target:
                    exit_price = target_price * slip_factor_sell
                    exit_reason = "TARGET_HIT"
                elif (t - entry_idx) >= 30:
                    # Max hold period 30 bars
                    exit_price = float(close.iloc[t]) * slip_factor_sell
                    exit_reason = "TIME_EXIT"

                if exit_price is not None:
                    # Calculate PnL with commissions
                    gross_pnl = (exit_price - entry_price) * shares
                    cost_total = (entry_price * shares * buy_fee) + (exit_price * shares * sell_fee)
                    net_pnl = gross_pnl - cost_total
                    ret_pct = (exit_price / entry_price - 1.0) * 100.0

                    trades.append({
                        "entry_idx": entry_idx,
                        "exit_idx": t,
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "shares": shares,
                        "net_pnl": round(net_pnl, 2),
                        "return_pct": round(ret_pct, 2),
                        "reason": exit_reason
                    })
                    in_trade = False

        # Summary Metrics
        n_trades = len(trades)
        if n_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "net_profit": 0.0,
                "max_drawdown_pct": 0.0,
                "note": "Tidak ada sinyal trade yang terpicu dalam rentang data"
            }

        wins = [t for t in trades if t["net_pnl"] > 0]
        losses = [t for t in trades if t["net_pnl"] <= 0]
        win_rate = round(len(wins) / n_trades, 3)

        gross_profit = sum(t["net_pnl"] for t in wins)
        gross_loss = abs(sum(t["net_pnl"] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0

        # Equity Curve and Drawdown
        pnl_series = [t["net_pnl"] for t in trades]
        equity = initial_capital + np.cumsum(pnl_series)
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / peak
        max_dd_pct = round(float(abs(dd.min()) * 100.0), 2)

        # Statistical Significance: Permutation null test
        p_val = self._permutation_test(pnl_series)

        return {
            "market": market,
            "total_trades": n_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_profit": round(sum(pnl_series), 2),
            "max_drawdown_pct": max_dd_pct,
            "p_value_significance": p_val,
            "statistically_significant": bool(p_val < 0.05),
            "costs_deducted": self.costs,
            "bias_checks": {
                "look_ahead_bias": "FREE (t signal -> t+1 open execution)",
                "survivorship_bias_warning": "Data gratis mengabaikan saham delisting; hasil historis memiliki bias optimisme"
            }
        }

    def _permutation_test(self, returns: List[float], n_permutations: int = 500) -> float:
        """Tests if the average trade return is statistically distinct from zero."""
        if len(returns) < 5:
            return 1.0
        obs_mean = np.mean(returns)
        arr = np.array(returns)
        rng = np.random.default_rng(42)
        count = 0
        for _ in range(n_permutations):
            # Rademacher sign-flip permutation
            signs = rng.choice([-1, 1], size=len(arr))
            if np.mean(arr * signs) >= obs_mean:
                count += 1
        return round(float(count / n_permutations), 3)

backtest_engine = BacktestEngine()
