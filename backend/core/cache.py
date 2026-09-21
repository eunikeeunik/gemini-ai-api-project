"""
EquityLens AI - Cache with TTL and Stale-While-Error
Uses SQLite persistence + In-Memory LRU for high performance
"""
import sqlite3
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional, Tuple, Callable
from functools import wraps
from backend.core.config import settings

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
def _json_serial_default(obj: Any) -> Any:
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


class CacheManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self._memory_cache = {}  # key -> (data, expires_at, as_of)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_store (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    as_of TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_store(expires_at)")
            conn.commit()

    def get(self, key: str) -> Optional[dict]:
        """Returns fresh data if not expired, else None"""
        now = time.time()
        # Check memory
        if key in self._memory_cache:
            data, expires_at, as_of = self._memory_cache[key]
            if now < expires_at:
                return data

        # Check DB
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data, expires_at, as_of FROM cache_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                raw_data, expires_at, as_of = row
                if now < expires_at:
                    val = json.loads(raw_data)
                    self._memory_cache[key] = (val, expires_at, as_of)
                    return val
        return None

    def get_stale(self, key: str) -> Optional[dict]:
        """Returns cached data even if expired, adding stale=True flag"""
        # Check memory
        if key in self._memory_cache:
            data, _, as_of = self._memory_cache[key]
            if isinstance(data, dict):
                data = dict(data)
                data["stale"] = True
            return data

        # Check DB
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data, as_of FROM cache_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                raw_data, as_of = row
                val = json.loads(raw_data)
                if isinstance(val, dict):
                    val["stale"] = True
                return val
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60, as_of: Optional[str] = None):
        now = time.time()
        expires_at = now + ttl_seconds
        as_of_str = as_of or now_utc_iso()
        
        # Memory
        self._memory_cache[key] = (value, expires_at, as_of_str)

        # DB
        raw_data = json.dumps(value, default=_json_serial_default)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO cache_store (key, data, expires_at, as_of)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    data = excluded.data,
                    expires_at = excluded.expires_at,
                    as_of = excluded.as_of
            """, (key, raw_data, expires_at, as_of_str))
            conn.commit()

    def delete(self, key: str):
        self._memory_cache.pop(key, None)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_store WHERE key = ?", (key,))
            conn.commit()

    def clear(self):
        self._memory_cache.clear()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_store")
            conn.commit()

cache = CacheManager()

def ttl_cache(ttl_seconds: int = 60, key_prefix: str = ""):
    """Decorator for caching function returns with TTL & stale fallback"""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key_parts = [key_prefix or fn.__name__]
            if args:
                key_parts.extend([str(a) for a in args])
            if kwargs:
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)

            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            try:
                result = fn(*args, **kwargs)
                if result is not None:
                    cache.set(cache_key, result, ttl_seconds=ttl_seconds)
                return result
            except Exception as e:
                # Stale-while-error
                stale_val = cache.get_stale(cache_key)
                if stale_val is not None:
                    return stale_val
                raise e
        return wrapper
    return decorator
