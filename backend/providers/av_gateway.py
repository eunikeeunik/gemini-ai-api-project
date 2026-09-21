"""
EquityLens AI - Alpha Vantage Gateway & QuotaGuard (Fase 17)
Enforces strict 25 requests/day and 5 requests/minute limits.
All Alpha Vantage calls MUST pass through this gateway.
Direct calls from frontend or LLM tools are strictly forbidden.
"""
import time
import sqlite3
from typing import Dict, Any, Optional
import httpx

from backend.core.config import settings
from backend.core.errors import QuotaExceededError, ProviderError
from backend.core.cache import cache

class QuotaGuard:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self.daily_limit = settings.ALPHAVANTAGE_DAILY_LIMIT - settings.ALPHAVANTAGE_SAFETY_MARGIN  # e.g. 25 - 2 = 23
        self.burst_limit = 5  # Max 5 calls per minute
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS av_quota_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    called_at REAL NOT NULL,
                    endpoint TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.commit()

    def can_call(self) -> bool:
        """Checks if current call will stay within daily and burst limits."""
        now = time.time()
        start_of_day = now - (now % 86400)
        one_min_ago = now - 60.0

        with sqlite3.connect(self.db_path) as conn:
            # Daily count
            daily_count = conn.execute(
                "SELECT COUNT(*) FROM av_quota_log WHERE called_at >= ?", (start_of_day,)
            ).fetchone()[0]
            if daily_count >= self.daily_limit:
                return False

            # Burst count (last 60 seconds)
            burst_count = conn.execute(
                "SELECT COUNT(*) FROM av_quota_log WHERE called_at >= ?", (one_min_ago,)
            ).fetchone()[0]
            if burst_count >= self.burst_limit:
                return False

        return True

    def record_call(self, endpoint: str, status: str = "SUCCESS"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO av_quota_log (called_at, endpoint, status) VALUES (?, ?, ?)",
                (time.time(), endpoint, status)
            )
            conn.commit()

    def get_quota_status(self) -> Dict[str, Any]:
        now = time.time()
        start_of_day = now - (now % 86400)
        with sqlite3.connect(self.db_path) as conn:
            daily_used = conn.execute(
                "SELECT COUNT(*) FROM av_quota_log WHERE called_at >= ?", (start_of_day,)
            ).fetchone()[0]

        return {
            "daily_limit": settings.ALPHAVANTAGE_DAILY_LIMIT,
            "safety_ceiling": self.daily_limit,
            "daily_used": daily_used,
            "daily_remaining": max(0, self.daily_limit - daily_used),
            "is_enabled": settings.ALPHAVANTAGE_ENABLED
        }


class AlphaVantageGateway:
    def __init__(self):
        self.guard = QuotaGuard()
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch(self, function: str, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Guarded Alpha Vantage request. Throws QuotaExceededError if quota exhausted.
        """
        if not settings.ALPHAVANTAGE_ENABLED or not settings.ALPHAVANTAGE_API_KEY:
            raise QuotaExceededError("Alpha Vantage tidak aktif atau API key belum diisi. Gunakan Yahoo/AkShare.")

        if not self.guard.can_call():
            self.guard.record_call(function, status="BLOCKED_QUOTA")
            raise QuotaExceededError(
                f"Batas kuota harian/menit Alpha Vantage tercapai ({self.guard.daily_limit}/hari). Permintaan dialihkan."
            )

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": settings.ALPHAVANTAGE_API_KEY,
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.base_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if "Note" in data or "Information" in data:
                        # API limit message returned by Alpha Vantage
                        self.guard.record_call(function, status="AV_RATE_LIMIT")
                        raise QuotaExceededError("Pesan batasan kuota diterima dari Alpha Vantage.")
                    
                    self.guard.record_call(function, status="SUCCESS")
                    return data
                else:
                    self.guard.record_call(function, status=f"HTTP_{resp.status_code}")
                    raise ProviderError(f"Alpha Vantage HTTP error: {resp.status_code}")
        except Exception as e:
            if not isinstance(e, (QuotaExceededError, ProviderError)):
                self.guard.record_call(function, status="EXCEPTION")
            raise e

av_gateway = AlphaVantageGateway()
