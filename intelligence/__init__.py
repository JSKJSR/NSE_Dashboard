"""
Market Intelligence Module
MVP Version 1.0

Provides real-time market news aggregation, sentiment analysis,
event classification, and priority-based alerting.
"""

from intelligence.news_fetcher import NewsFetcher, fetch_latest_news, fetch_india_news
from intelligence.sentiment import (
    SentimentAnalyzer,
    analyze_sentiment,
    get_market_sentiment,
    VADER_AVAILABLE,
    FINBERT_AVAILABLE
)
from intelligence.classifier import (
    EventClassifier,
    classify_news,
    detect_critical_events,
    RateChangeDetector,
    GeopoliticalDetector
)
from intelligence.storage import IntelligenceStorage, get_storage

# Widget imports are lazy - only imported when used (requires streamlit)
def render_intelligence_widget(*args, **kwargs):
    from intelligence.widget import render_intelligence_widget as _render
    return _render(*args, **kwargs)

def render_compact_widget(*args, **kwargs):
    from intelligence.widget import render_compact_widget as _render
    return _render(*args, **kwargs)

def render_intelligence_page(*args, **kwargs):
    from intelligence.widget import render_intelligence_page as _render
    return _render(*args, **kwargs)

__version__ = "1.0.0"

__all__ = [
    # News Fetcher
    "NewsFetcher",
    "fetch_latest_news",
    "fetch_india_news",

    # Sentiment Analysis
    "SentimentAnalyzer",
    "analyze_sentiment",
    "get_market_sentiment",
    "VADER_AVAILABLE",
    "FINBERT_AVAILABLE",

    # Classification
    "EventClassifier",
    "classify_news",
    "detect_critical_events",
    "RateChangeDetector",
    "GeopoliticalDetector",

    # Storage
    "IntelligenceStorage",
    "get_storage",

    # Widget
    "render_intelligence_widget",
    "render_compact_widget",
    "render_intelligence_page",
]
