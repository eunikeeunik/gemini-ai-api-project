"""
EquityLens AI - Core Errors
Standardized JSON error envelope: { "error": { "code", "message", "provider" } }
"""
from typing import Optional, Any
from fastapi import Request
from fastapi.responses import JSONResponse

class EquityLensError(Exception):
    def __init__(self, code: str, message: str, provider: Optional[str] = None, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.provider = provider or "equitylens"
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict:
        err = {
            "code": self.code,
            "message": self.message,
            "provider": self.provider
        }
        if self.details is not None:
            err["details"] = self.details
        return {"error": err}

class ProviderError(EquityLensError):
    def __init__(self, provider: str, message: str, code: str = "PROVIDER_ERROR", status_code: int = 502, details: Optional[Any] = None):
        super().__init__(code=code, message=message, provider=provider, status_code=status_code, details=details)

class DataNotFoundError(EquityLensError):
    def __init__(self, symbol: str, provider: str = "internal", message: Optional[str] = None):
        super().__init__(
            code="DATA_NOT_FOUND",
            message=message or f"Data tidak ditemukan untuk simbol: {symbol}",
            provider=provider,
            status_code=404
        )

class QuotaExceededError(EquityLensError):
    def __init__(self, provider: str, message: str = "Batas kuota provider terlampaui"):
        super().__init__(code="QUOTA_EXCEEDED", message=message, provider=provider, status_code=429)

class ValidationError(EquityLensError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(code="VALIDATION_ERROR", message=message, provider="validator", status_code=422, details=details)

async def equitylens_exception_handler(request: Request, exc: EquityLensError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
