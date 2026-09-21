"""
EquityLens AI - News Sentiment Aggregator (Fase 10)
Applies age-decay weighting across live news items for the ticker
and produces structured sentiment metrics.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math
from backend.providers.news_rss import get_cached_news

def analyze_sentiment(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """
    Computes sentiment score (-1.0 to +1.0) with exponential time decay
    so breaking news has higher influence than older articles.
    """
    clean_sym = symbol.upper().replace(".JK", "").replace("IDX:", "").replace("US:", "")
    articles = get_cached_news(symbol=clean_sym, limit=limit)
    
    if not articles:
        # Fallback to general market news if no specific ticker news
        articles = get_cached_news(symbol=None, limit=limit)

    if not articles:
        return {
            "symbol": clean_sym,
            "score": 0.0,
            "n_articles": 0,
            "sentiment_label": "netral",
            "drivers": [],
            "note": "Tidak ada artikel berita terkini"
        }

    now = datetime.now(timezone.utc)
    weighted_sum = 0.0
    weight_total = 0.0
    drivers = []
    
    for art in articles:
        sent = art.get("sentiment", {})
        score = float(sent.get("score", 0.0))
        
        # Calculate age in hours
        pub_str = art.get("published_at", "")
        age_hours = 12.0
        try:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            age_hours = max(0.1, (now - pub_dt).total_seconds() / 3600.0)
        except Exception:
            pass

        # Exponential decay: half-life = 48 hours
        decay_weight = math.exp(-0.693 * (age_hours / 48.0))
        weighted_sum += score * decay_weight
        weight_total += decay_weight

        if abs(score) >= 0.4:
            drivers.append({
                "title": art.get("title"),
                "source": art.get("source"),
                "sentiment": sent.get("label"),
                "url": art.get("url")
            })

    final_score = (weighted_sum / weight_total) if weight_total > 0 else 0.0
    final_score = round(max(-1.0, min(1.0, final_score)), 2)

    if final_score >= 0.2:
        label = "positif"
    elif final_score <= -0.2:
        label = "negatif"
    else:
        label = "netral"

    return {
        "symbol": clean_sym,
        "score": final_score,
        "n_articles": len(articles),
        "sentiment_label": label,
        "drivers": drivers[:5],
        "sources_used": list(set(a.get("source", "RSS") for a in articles))
    }
