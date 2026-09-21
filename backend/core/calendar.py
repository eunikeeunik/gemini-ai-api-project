"""
EquityLens AI - Exchange Calendar & Market Status
Determines whether market is open, closed, or holiday for IDX, SGX, US, and CN.
"""
from datetime import datetime, timezone
import zoneinfo
from typing import Dict, Any

MARKET_CALENDARS = {
    "IDX": {"tz": "Asia/Jakarta", "code": "XIDX", "open": (9, 0), "close": (16, 0), "delay_note": "tertunda ±15 menit"},
    "SGX": {"tz": "Asia/Singapore", "code": "XSES", "open": (9, 0), "close": (17, 0), "delay_note": "tertunda ±15 menit"},
    "US": {"tz": "America/New_York", "code": "XNYS", "open": (9, 30), "close": (16, 0), "delay_note": "real-time / tertunda ±15 menit"},
    "SSE": {"tz": "Asia/Shanghai", "code": "XSHG", "open": (9, 30), "close": (15, 0), "delay_note": "tertunda ±15 menit"},
    "SZSE": {"tz": "Asia/Shanghai", "code": "XSHE", "open": (9, 30), "close": (15, 0), "delay_note": "tertunda ±15 menit"},
}

_CALENDAR_INSTANCES = {}

def _get_calendar(code: str):
    if code in _CALENDAR_INSTANCES:
        return _CALENDAR_INSTANCES[code]
    try:
        import exchange_calendars as xcals
        cal = xcals.get_calendar(code)
        _CALENDAR_INSTANCES[code] = cal
        return cal
    except Exception:
        return None

def get_market_status(market: str) -> Dict[str, Any]:
    market = market.upper()
    info = MARKET_CALENDARS.get(market, MARKET_CALENDARS["IDX"])
    tz = zoneinfo.ZoneInfo(info["tz"])
    now_local = datetime.now(tz)
    now_utc = datetime.now(timezone.utc)
    
    cal = _get_calendar(info["code"])
    is_open = False
    status_label = "Tutup"
    
    if cal:
        try:
            is_open = cal.is_open_at_time(now_utc)
            status_label = "Buka" if is_open else "Pasar Tutup"
        except Exception:
            # Fallback to local time heuristic
            is_weekday = now_local.weekday() < 5
            open_h, open_m = info["open"]
            close_h, close_m = info["close"]
            current_time = (now_local.hour, now_local.minute)
            is_open = is_weekday and ((open_h, open_m) <= current_time <= (close_h, close_m))
            status_label = "Buka" if is_open else "Pasar Tutup"
    else:
        is_weekday = now_local.weekday() < 5
        open_h, open_m = info["open"]
        close_h, close_m = info["close"]
        current_time = (now_local.hour, now_local.minute)
        is_open = is_weekday and ((open_h, open_m) <= current_time <= (close_h, close_m))
        status_label = "Buka" if is_open else "Pasar Tutup"

    return {
        "market": market,
        "is_open": is_open,
        "status_label": status_label,
        "local_time": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "delay_note": info["delay_note"]
    }
