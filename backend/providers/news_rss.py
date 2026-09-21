"""
EquityLens AI - Real News RSS Aggregator
Fetches, normalizes, deduplicates, and filters live financial news from verified media.
Never copies full article content (only title, short summary, source, url, published_at).
"""
import asyncio
import httpx
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
from backend.core.cache import cache, now_utc_iso

RSS_FEEDS = {
    "Antara Bisnis": "https://www.antaranews.com/rss/ekonomi-bisnis.xml",
    "Antara Bursa": "https://www.antaranews.com/rss/ekonomi-bursa.xml",
    "Kontan": "https://rss.kontan.co.id/news/keuangan",
    "CNN Indonesia": "https://www.cnnindonesia.com/ekonomi/rss",
    "Detik Finance": "https://finance.detik.com/rss",
}

POSITIVE_WORDS = {"naik", "menguat", "tumbuh", "laba", "untung", "dividen", "rekor", "ekspansi", "surplus", "bullish", "lonjakan", "akuisisi"}
NEGATIVE_WORDS = {"turun", "melemah", "rugi", "merosot", "anjlok", "defisit", "bearish", "suspensi", "pailit", "penurunan", "inflasi", "utang"}

def estimate_simple_sentiment(text: str) -> Dict[str, Any]:
    lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
    if pos > neg:
        return {"label": "positif", "score": 0.5 + min(0.4, (pos - neg) * 0.1)}
    elif neg > pos:
        return {"label": "negatif", "score": -0.5 - min(0.4, (neg - pos) * 0.1)}
    return {"label": "netral", "score": 0.0}

def normalize_entry(source_name: str, entry: Any) -> Dict[str, Any]:
    title = entry.get("title", "").strip()
    summary = entry.get("summary", "") or entry.get("description", "")
    # Clean HTML tags from summary if any
    import re
    clean_summary = re.sub(r"<[^>]+>", "", summary).strip()
    if len(clean_summary) > 200:
        clean_summary = clean_summary[:197] + "..."

    link = entry.get("link", "").strip()
    pub = entry.get("published", "") or entry.get("pubDate", "")
    if not pub:
        pub = now_utc_iso()

    sentiment = estimate_simple_sentiment(f"{title} {clean_summary}")

    return {
        "title": title,
        "summary": clean_summary or title,
        "url": link,
        "source": source_name,
        "published_at": pub,
        "lang": "id",
        "sentiment": sentiment,
        "id": hashlib.md5(link.encode("utf-8") if link else title.encode("utf-8")).hexdigest()
    }

async def fetch_single_feed(client: httpx.AsyncClient, name: str, url: str) -> List[Dict[str, Any]]:
    try:
        resp = await client.get(url, timeout=5.0, follow_redirects=True)
        if resp.status_code == 200:
            parsed = feedparser.parse(resp.text)
            return [normalize_entry(name, e) for e in parsed.entries if e.get("title")]
    except Exception:
        pass
    return []

async def get_live_news(ticker: Optional[str] = None, topic: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
    cache_key = f"news_feed:{ticker or 'all'}:{topic or 'all'}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {"User-Agent": "EquityLensAI/1.0 (Equity Research Bot; contact@equitylens.ai)"}
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [fetch_single_feed(client, name, url) for name, url in RSS_FEEDS.items()]
        feed_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    seen_urls = set()
    seen_titles = set()

    for res in feed_results:
        if isinstance(res, list):
            for art in res:
                url = art["url"]
                title_key = art["title"].lower()[:40]
                if url and url not in seen_urls and title_key not in seen_titles:
                    seen_urls.add(url)
                    seen_titles.add(title_key)
                    all_articles.append(art)

    # Filter by ticker or topic keyword if provided
    query = (ticker or topic or "").lower().strip()
    if query:
        filtered = []
        for a in all_articles:
            text = f"{a['title']} {a['summary']}".lower()
            if query in text:
                filtered.append(a)
        if filtered:
            all_articles = filtered

    # Sort and slice
    results = all_articles[:limit]
    cache.set(cache_key, results, ttl_seconds=300)  # 5 minutes
    return results


def get_cached_news(symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Synchronous getter for cached news feed with event loop fallback."""
    cache_key = f"news_feed:{symbol or 'all'}:all:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, get_live_news(ticker=symbol, limit=limit)).result()
        else:
            return loop.run_until_complete(get_live_news(ticker=symbol, limit=limit))
    except Exception:
        return []
