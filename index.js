import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenAI } from '@google/genai';
import YahooFinance from 'yahoo-finance2';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const yahooFinance = new YahooFinance({ suppressNotices: ['yahooSurvey'] });

const GEMINI_MODEL = "gemini-3.5-flash";

app.use(cors());
app.use(express.json());

app.use(express.static(path.join(__dirname, 'public')));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Server ready on http://localhost:${PORT}`));

/**
 * Mengambil data pasar real-time dari Yahoo Finance
 */
async function getStockQuote(ticker) {
    const cleanTicker = ticker.toUpperCase().replace(/[^A-Z0-9^.]/g, '');
    if (!cleanTicker) return null;

    // Coba dengan akhiran .JK untuk saham Indonesia atau kode asli untuk US
    const candidates = cleanTicker.includes('.') 
        ? [cleanTicker] 
        : [cleanTicker.length === 4 ? `${cleanTicker}.JK` : cleanTicker, `${cleanTicker}.JK`, cleanTicker];

    for (const sym of candidates) {
        try {
            const q = await yahooFinance.quote(sym);
            if (q && q.regularMarketPrice !== undefined) {
                return {
                    symbol: q.symbol,
                    name: q.shortName || q.longName || cleanTicker,
                    currency: q.currency || 'IDR',
                    price: q.regularMarketPrice,
                    change: q.regularMarketChange,
                    changePercent: q.regularMarketChangePercent !== undefined ? q.regularMarketChangePercent.toFixed(2) + '%' : 'N/A',
                    dayRange: `${q.regularMarketDayLow || '-'} - ${q.regularMarketDayHigh || '-'}`,
                    fiftyTwoWeekRange: `${q.fiftyTwoWeekLow || '-'} - ${q.fiftyTwoWeekHigh || '-'}`,
                    pe: q.trailingPE ? q.trailingPE.toFixed(2) : 'N/A',
                    pbv: q.priceToBook ? q.priceToBook.toFixed(2) : 'N/A',
                    marketCap: q.marketCap ? (q.marketCap >= 1e12 ? (q.marketCap / 1e12).toFixed(2) + ' T' : (q.marketCap / 1e9).toFixed(2) + ' B') : 'N/A'
                };
            }
        } catch (e) {
            // lanjut ke kandidat berikutnya jika gagal
        }
    }
    return null;
}

/**
 * Ekstraksi ticker saham dari pesan user
 */
function extractStockTickers(text) {
    if (!text) return [];
    const matches = text.toUpperCase().match(/\b[A-Z]{3,5}(\.JK)?\b/g) || [];
    const exclusions = new Set(['APA', 'DAN', 'YANG', 'DARI', 'DENGAN', 'UNTUK', 'BISA', 'HALO', 'CHAT', 'CARA', 'CALL', 'PADA', 'RISK', 'LOSS', 'STOP', 'SELL', 'BUAT', 'SAHAM', 'IHSG', 'DATA', 'BACA', 'BEDA', 'INFO', 'VIEW']);
    const unique = [...new Set(matches.filter(m => !exclusions.has(m)))];
    return unique.slice(0, 3); // Batasi maksimal 3 ticker per pesan
}

// Endpoint GET untuk mengecek harga saham secara langsung
app.get('/api/stock/:symbol', async (req, res) => {
    try {
        const data = await getStockQuote(req.params.symbol);
        if (!data) return res.status(404).json({ error: 'Data saham tidak ditemukan' });
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/chat', async(req, res) => {
    const { conversation } = req.body;
    try {
        if (!Array.isArray(conversation)) throw new Error('Messages must be an array');
        
        // Cek ticker saham pada pesan terakhir pengguna
        const lastUserMsg = [...conversation].reverse().find(m => m.role === 'user');
        let marketDataContext = '';

        if (lastUserMsg && lastUserMsg.text) {
            const tickers = extractStockTickers(lastUserMsg.text);
            if (tickers.length > 0) {
                const quotePromises = tickers.map(t => getStockQuote(t));
                const quotes = (await Promise.all(quotePromises)).filter(Boolean);

                if (quotes.length > 0) {
                    marketDataContext = `\n\n[DATA PASAR REAL-TIME TERKINI (Yahoo Finance)]:\n` + 
                        quotes.map(q => `• ${q.symbol} (${q.name}): Harga ${q.currency} ${q.price} (${q.changePercent}), Rentang Hari Ini: ${q.dayRange}, 52-Wk Range: ${q.fiftyTwoWeekRange}, PER: ${q.pe}, PBV: ${q.pbv}, Market Cap: ${q.marketCap}`).join('\n') +
                        `\n(Gunakan data harga & metrik live di atas sebagai dasar analisis terkini Anda)`;
                }
            }
        }

        const contents = conversation.map(({ role, text }, idx) => {
             const isLastUser = (idx === conversation.length - 1 && role === 'user');
             return {
                 role,
                 parts: [{ text: isLastUser && marketDataContext ? `${text}${marketDataContext}` : text }]
             };
        });

        const response = await ai.models.generateContent({
            model: GEMINI_MODEL,
            contents,
            config: {
                systemInstruction: `
Anda adalah "EquityLens AI", seorang Analis Senior Pasar Modal, Chartered Financial Analyst (CFA), dan Spesialis Riset Ekuitas berpengalaman lebih dari 15 tahun di pasar modal Indonesia (BEI / IDX) dan global (US Stock Market).

Misi utama Anda: Menyajikan analisis saham yang mendalam, terstruktur, objektif, dan berbasis data keuangan serta teknikal nyata untuk membantu investor dan trader membuat keputusan yang terukur.

Ketika pengguna meminta analisis suatu saham (misalnya BBCA, BBRI, ASII, NVDA, AAPL, dsb.), susun analisis secara komprehensif mengikuti kerangka standar riset institusional berikut:

1. **Profil Singkat & Model Bisnis (Moat)**:
   - Ringkasan bisnis inti, segmen penghasil laba utama, dan keunggulan kompetitif (economic moat).

2. **Analisis Fundamental & Metrik Keuangan**:
   - Pertumbuhan Pendapatan (Revenue Growth) & Margin Laba Bersih (Net Profit Margin).
   - Rasio Profitabilitas: ROE (Return on Equity) dan ROA.
   - Rasio Kesehatan Keuangan & Solvabilitas: DER (Debt to Equity Ratio) dan Cash Flow operasional.
   - Dividen: Historis Dividend Yield dan Payout Ratio (jika relevan).

3. **Valuasi Saham**:
   - Evaluasi rasio valuasi utama: PER (Price to Earnings), PBV (Price to Book Value), EV/EBITDA.
   - Bandingkan dengan rata-rata historis (5-year mean) dan peers/kompetitor di industri yang sama.
   - Kesimpulan valuasi: Apakah saat ini tergolong *Undervalued* (Murah), *Fairly Valued* (Wajar), atau *Overvalued* (Mahal).

4. **Analisis Teknikal & Price Action**:
   - Struktur Tren Utama: Bullish / Bearish / Sideways (Daily & Weekly timeframe).
   - Moving Average Kunci: Posisi harga terhadap MA20, MA50, dan MA200.
   - Momentum & Indikator: RSI (kondisi Overbought/Oversold/Neutral) dan MACD.
   - Level Kunci: Area Support kuat & Resistance terdekat.

5. **Katalis Pasar, Sentimen & Arus Dana (Foreign Flow / Volume)**:
   - Katalis penggerak (misal: rilis laporan keuangan, corporate action, tren komoditas, suku bunga BI / The Fed).
   - Karakteristik akumulasi atau distribusi volume transaksi.

6. **Rencana Eksekusi & Manajemen Risiko (Trading/Investing Plan)**:
   - Skenario Masuk: Buy on Weakness (BoW) atau Buy on Breakout (BoB).
   - Level Acuan Angka:
     * Area Beli (Entry Zone)
     * Target Price 1 & Target Price 2 (Take Profit)
     * Level Stop Loss / Cut Loss (Batas Toleransi Risiko Ketat)
     * Risk-to-Reward Ratio (usahakan minimal 1:2).

7. **Format & Etika**:
   - Gunakan format Markdown yang sangat rapi: tabel perbandingan jika perlu, bullet points, dan penekanan tebal (bold).
   - Gunakan gaya bahasa profesional, lugas, santun, dan mudah dipahami baik oleh pemula maupun investor berpengalaman.
   - Jawab pertanyaan seputar pasar modal, saham, ekonomi makro, dan strategi investasi. Jika user bertanya hal di luar topik keuangan/investasi, arahkan kembali dengan sopan ke analisa saham dan pasar modal.
   - **WAJIB MENYERTAKAN DISCLAIMER** di akhir setiap analisis:
     "⚠️ **Disclaimer:** *Analisis ini disusun semata-mata untuk tujuan edukasi dan riset informasi pasar modal, bukan merupakan anjuran atau ajakan mutlak untuk membeli/menjual instrumen keuangan tertentu. Investasi saham mengandung risiko fluktuasi nilai modal. Lakukan riset mandiri (Do Your Own Research - DYOR) dan sesuaikan dengan profil risiko serta modal Anda.*"
`
            }
        });
        res.status(200).json({ result: response.text });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});