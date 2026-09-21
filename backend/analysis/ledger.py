"""
EquityLens AI - Prediction Ledger & Track Record (Fase 11)
Maintains honest historical log of model forecasts and resolves outcomes
when the time horizon expires. Tracks actual empirical hit-rate.
"""
import sqlite3
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings
from backend.core.cache import now_utc_iso

class PredictionLedger:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    horizon_days INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    target_price REAL,
                    stop_loss REAL,
                    p_target REAL,
                    p_stop REAL,
                    model_edge INTEGER NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    resolved_at TEXT,
                    hit_target INTEGER,
                    actual_return REAL
                )
            """)
            conn.commit()

    def record_prediction(
        self,
        symbol: str,
        market: str,
        entry_price: float,
        horizon_days: int = 20,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        p_target: float = 0.5,
        p_stop: float = 0.5,
        model_edge: bool = False
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO prediction_ledger (
                    symbol, market, created_at, horizon_days, entry_price,
                    target_price, stop_loss, p_target, p_stop, model_edge, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """, (
                symbol, market, now_utc_iso(), horizon_days, entry_price,
                target_price, stop_loss, p_target, p_stop, 1 if model_edge else 0
            ))
            conn.commit()
            return cur.lastrowid

    def get_track_record(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Calculates running accuracy and hit-rate of resolved predictions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM prediction_ledger WHERE symbol = ?", (symbol,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM prediction_ledger").fetchall()

        total = len(rows)
        resolved = [r for r in rows if r["status"] == "RESOLVED"]
        resolved_count = len(resolved)

        if resolved_count == 0:
            return {
                "total_predictions": total,
                "resolved": 0,
                "pending": total,
                "hit_rate": None,
                "avg_return_pct": 0.0,
                "note": "Belum ada prediksi yang mencapai masa horizon evaluasi"
            }

        hits = sum(1 for r in resolved if r["hit_target"] == 1)
        hit_rate = round(hits / resolved_count, 3)
        returns = [r["actual_return"] for r in resolved if r["actual_return"] is not None]
        avg_ret = round(sum(returns) / len(returns), 2) if returns else 0.0

        return {
            "total_predictions": total,
            "resolved": resolved_count,
            "pending": total - resolved_count,
            "hits": hits,
            "hit_rate": hit_rate,
            "avg_return_pct": avg_ret,
            "brier_score": None
        }

ledger = PredictionLedger()
