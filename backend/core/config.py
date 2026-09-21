import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

class Settings:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        
        self.CACHE_DB_PATH = os.getenv("CACHE_DB_PATH", str(ROOT_DIR / "cache.sqlite"))
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:8000,http://127.0.0.1:8000")
        
        self.ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
        self.ALPHAVANTAGE_ENABLED = os.getenv("ALPHAVANTAGE_ENABLED", "false").lower() in ("true", "1", "yes")
        self.ALPHAVANTAGE_DAILY_LIMIT = int(os.getenv("ALPHAVANTAGE_DAILY_LIMIT", "25"))
        self.ALPHAVANTAGE_SAFETY_MARGIN = int(os.getenv("ALPHAVANTAGE_SAFETY_MARGIN", "2"))
        
        self.FRED_API_KEY = os.getenv("FRED_API_KEY", "")
        self.BPS_API_KEY = os.getenv("BPS_API_KEY", "")
        self.SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "EquityLensAI research@equitylens.ai")
        
        self.ANALYSIS_CACHE_MINUTES = int(os.getenv("ANALYSIS_CACHE_MINUTES", "15"))
        self.STATIC_DIR = str(ROOT_DIR / "gemini-chatbot-api" / "public")
        self.PORT = int(os.getenv("PORT", "8000"))

    @property
    def cors_origins(self) -> List[str]:
        return [orig.strip() for orig in self.ALLOWED_ORIGINS.split(",") if orig.strip()]

settings = Settings()
