"""
EquityLens AI - Gemini Agent Integration (Fase 13)
Implements institutional equity analysis narrator with function calling,
grounding validation, and strict adherence to calculated metrics.
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from google import genai
from google.genai import types

from backend.core.config import settings
from backend.agent.validator import validate_narrative
from backend.providers.yahoo import (
    get_quote,
    get_history,
    get_fundamentals,
    get_market_overview as yahoo_market_overview,
    resolve_symbol
)
from backend.providers.news_rss import get_cached_news
from backend.providers.brokerflow import get_broker_flow
from backend.analysis.report import generate_analysis_report
from backend.analysis.technicals import calculate_technicals
from backend.analysis.candles import analyze_candlesticks
from backend.analysis.volume import analyze_volume
from backend.analysis.pressure import analyze_buy_sell_pressure
from backend.analysis.fundamentals import analyze_fundamentals
from backend.analysis.valuation import analyze_valuation

# System Instruction per Spec Sections 7.2 & 13.2
SYSTEM_INSTRUCTION = """
Anda adalah "EquityLens AI", seorang Analis Senior Pasar Modal, Chartered Financial Analyst (CFA), dan Spesialis Riset Ekuitas berpengalaman di pasar modal Indonesia (IDX), Amerika Serikat (US), Singapura (SGX), dan China (SSE).

Misi utama Anda: Menyajikan analisis pasar saham yang mendalam, terstruktur, objektif, dan jujur terhadap ketidakpastian. Anda HANYA menarasikan data dari tools dan objek AnalysisReport.

ATURAN WAJIB (STRICT ENGINE CONSTRAINTS):
1. DILARANG menghitung atau mengarang angka. Kutip semua angka persis apa adanya dari hasil tool, lengkap dengan periode dan as_of.
2. WAJIB menampilkan secara eksplisit:
   - Skor Kepercayaan (Confidence): Rendah / Sedang / Tinggi.
   - Kelengkapan Data (Data Completeness): Skor dan sebutkan data apa yang "tidak tersedia" jika < 100%.
   - Konflik antar dimensi jika ada (misalnya: teknikal bullish tapi sentimen/makro bearish).
3. PRAKIRAAN (FORECAST) & ARAH:
   - Sebutkan status `model_edge`. Jika model_edge bernilai false, Anda HARUS menyatakan secara jujur: "Tidak ada keunggulan statistik (edge) untuk memprediksi arah pasti harga; yang disajikan adalah rentang volatilitas probabilistik."
   - Sajikan skenario dalam probabilitas (misal: P(target tercapai lebih dulu) = 54%) dan rentang harga, BUKAN satu target harga pasti.
4. PROKSI & LABEL:
   - Bedakan secara tegas antara FAKTA (data transaksi real), INTERPRETASI, dan ASUMSI.
   - Analisis tekanan beli-jual dari harga dan volume WAJIB diberi label sebagai "PROKSI", bukan data aliran order (order book/broker flow riil).
5. INVALIDASI & KETIDAKPASTIAN:
   - Sertakan kondisi "Apa yang membatalkan skenario ini" (level stop loss struktural, penembusan resistance/support kunci, perubahan sentimen).
   - Cantumkan apa yang belum diketahui (unknowns/missing risks).
6. BERITA:
   - Parafrase secara ringkas intisari berita, sebutkan nama media penerbit dan tanggal rilis. Sertakan tautan sumber jika tersedia. Dilarang menyalin mentah paragraf berita.
7. ETIKA & LARANGAN:
   - DILARANG menggunakan kata kepastian ("pasti naik", "pasti untung", "dijamin", "100% cuan", "tanpa risiko").
   - WAJIB menyertakan disclaimer edukasi di akhir setiap analisis:
   
⚠️ **Disclaimer Edukasi:** *Analisis ini disusun semata-mata untuk tujuan edukasi dan riset informasi pasar modal, bukan merupakan rekomendasi investasi personal atau anjuran membeli/menjual instrumen tertentu. Setiap keputusan finansial sepenuhnya berada di bawah risiko dan tanggung jawab pengguna (DYOR).*
"""

# Tool function implementations
def tool_get_stock_quote(symbol: str) -> str:
    """Mengambil harga pasar real-time, perubahan harian, dan rentang harga suatu saham."""
    try:
        market, code = resolve_symbol(symbol)
        quote = get_quote(market, code)
        return json.dumps(quote, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal mengambil quote {symbol}: {str(e)}", "symbol": symbol})

def tool_get_full_analysis(symbol: str, horizon: str = "swing", mode: str = "deep") -> str:
    """
    Menghasilkan laporan komprehensif AnalysisReport (teknikal, candlestick, volume profile,
    tekanan beli-jual, fundamental DuPont & Piotroski, valuasi, trading plan, dan konfluensi).
    Parameter horizon: 'swing' (hari-minggu) atau 'positional' (bulan).
    Parameter mode: 'deep' (lengkap) atau 'brief' (ringkas).
    """
    try:
        report = generate_analysis_report(symbol=symbol, horizon=horizon, mode=mode)
        return json.dumps(report, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal menghasilkan laporan {symbol}: {str(e)}", "symbol": symbol})

def tool_get_technical_analysis(symbol: str) -> str:
    """Mengambil indikator teknikal: RSI, MACD, Bollinger Bands, ATR, Moving Average 20/50/100/200, dan Level S/R."""
    try:
        market, code = resolve_symbol(symbol)
        df = get_history(market, code, period="1y", interval="1d")
        tech = calculate_technicals(df)
        return json.dumps(tech, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal analisis teknikal {symbol}: {str(e)}"})

def tool_get_fundamental_analysis(symbol: str) -> str:
    """Mengambil analisis fundamental: DuPont 3-way, Piotroski F-score, Altman Z-Score, solvabilitas, dan margin."""
    try:
        market, code = resolve_symbol(symbol)
        fund = get_fundamentals(market, code)
        ratios = analyze_fundamentals(fund, market=market, symbol=code)
        return json.dumps(ratios, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal analisis fundamental {symbol}: {str(e)}"})

def tool_get_valuation_analysis(symbol: str) -> str:
    """Mengambil valuasi persentil 5 tahun PER/PBV, Nilai Wajar Graham, dan matriks sensitivitas DCF."""
    try:
        market, code = resolve_symbol(symbol)
        fund = get_fundamentals(market, code)
        quote = get_quote(market, code)
        val = analyze_valuation(fund, quote, market=market)
        return json.dumps(val, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal valuasi {symbol}: {str(e)}"})

def tool_get_candlestick_and_volume(symbol: str) -> str:
    """Mendeteksi pola candlestick dengan hit rate historis 5 tahun, Volume Profile (POC/VAH/VAL), OBV, dan CMF."""
    try:
        market, code = resolve_symbol(symbol)
        df = get_history(market, code, period="2y", interval="1d")
        tech = calculate_technicals(df)
        atr = tech.get("atr14", 1.0)
        candles = analyze_candlesticks(df, atr)
        volume = analyze_volume(df)
        return json.dumps({"candlestick": candles, "volume": volume}, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal analisis candle & volume {symbol}: {str(e)}"})

def tool_get_buy_sell_pressure(symbol: str) -> str:
    """Menghitung proksi tekanan beli vs jual dari Closed-to-Location Value (CLV) dan Volume Imbalance harian."""
    try:
        market, code = resolve_symbol(symbol)
        df = get_history(market, code, period="6mo", interval="1d")
        pressure = analyze_buy_sell_pressure(df)
        return json.dumps(pressure, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal tekanan beli/jual {symbol}: {str(e)}"})

def tool_get_stock_news(symbol: str, limit: int = 5) -> str:
    """Mengambil berita finansial terkini terkait emiten/saham tertentu dari feed media terpercaya."""
    try:
        news = get_cached_news(symbol=symbol, limit=limit)
        return json.dumps(news, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal mengambil berita {symbol}: {str(e)}"})

def tool_get_market_overview(market: str = "IDX") -> str:
    """Mengambil ringkasan pasar regional/global (IHSG, S&P 500, STI, SSE, USD/IDR)."""
    try:
        overview = yahoo_market_overview()
        return json.dumps(overview, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal mengambil ringkasan pasar {market}: {str(e)}"})

def tool_get_broker_flow(symbol: str) -> str:
    """Mengecek data aliran broker / bandarmologi / foreign flow. Mengembalikan status ketersediaan."""
    try:
        flow = get_broker_flow(symbol)
        return json.dumps(flow, default=str)
    except Exception as e:
        return json.dumps({"error": f"Gagal broker flow {symbol}: {str(e)}"})


ALL_AGENT_TOOLS = [
    tool_get_stock_quote,
    tool_get_full_analysis,
    tool_get_technical_analysis,
    tool_get_fundamental_analysis,
    tool_get_valuation_analysis,
    tool_get_candlestick_and_volume,
    tool_get_buy_sell_pressure,
    tool_get_stock_news,
    tool_get_market_overview,
    tool_get_broker_flow
]


class GeminiAgent:
    """Institutional Analysis Gemini Chat Agent."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key)

    def _create_chat_session(self, history: Optional[List[Dict[str, str]]] = None):
        """Creates a chat session with registered institutional equity tools."""
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=ALL_AGENT_TOOLS,
            temperature=0.2,
        )
        chat = self.client.chats.create(
            model=self.model_name,
            config=config
        )
        return chat

    async def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Executes chat turn with tool calling, and validates output grounding.
        """
        chat = self._create_chat_session(history)
        
        # Run in threadpool because genai sdk client is synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: chat.send_message(message))
        raw_text = response.text or ""

        # Validate narrative against grounding rules
        validation = validate_narrative(raw_text, {})

        return {
            "text": raw_text,
            "validation": validation
        }

    async def chat_stream(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Executes chat turn with automatic tool calling, then streams response chunks.
        """
        chat = self._create_chat_session(history)
        loop = asyncio.get_event_loop()

        # Execute chat message with tools resolution
        response = await loop.run_in_executor(None, lambda: chat.send_message(message))
        text = response.text or ""
        
        # Stream response in chunks for smooth UX
        chunk_size = 40
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
            await asyncio.sleep(0.02)


# Global singleton agent
gemini_agent = GeminiAgent()
