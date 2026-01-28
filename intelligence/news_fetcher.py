"""
News Fetcher Module
MVP Version - RSS feeds + Finnhub API
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import feedparser
import requests

from intelligence.config import RSS_FEEDS, FINNHUB_API_KEY

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetch news from multiple sources."""

    def __init__(self):
        self.finnhub_base = "https://finnhub.io/api/v1"
        self.seen_ids = set()  # Deduplication cache

    def fetch_all(self) -> List[Dict]:
        """Fetch news from all configured sources."""
        all_news = []

        # Fetch from RSS feeds (free, no API key)
        for source_name, feed_url in RSS_FEEDS.items():
            try:
                news = self._fetch_rss(source_name, feed_url)
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"RSS fetch failed for {source_name}: {e}")

        # Fetch from Finnhub if API key available
        if FINNHUB_API_KEY:
            try:
                finnhub_news = self._fetch_finnhub()
                all_news.extend(finnhub_news)
            except Exception as e:
                logger.warning(f"Finnhub fetch failed: {e}")

        # Deduplicate and sort by time
        unique_news = self._deduplicate(all_news)
        return sorted(unique_news, key=lambda x: x["timestamp"], reverse=True)

    def _fetch_rss(self, source_name: str, feed_url: str) -> List[Dict]:
        """Fetch and parse RSS feed."""
        news_items = []

        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:20]:  # Limit to 20 per source
                # Extract timestamp
                timestamp = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    timestamp = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    timestamp = datetime(*entry.updated_parsed[:6])
                else:
                    timestamp = datetime.now()

                # Skip old news (> 24 hours)
                if datetime.now() - timestamp > timedelta(hours=24):
                    continue

                # Create news item
                news_item = {
                    "id": self._generate_id(entry.get("title", "")),
                    "headline": entry.get("title", "").strip(),
                    "summary": entry.get("summary", entry.get("description", ""))[:500],
                    "url": entry.get("link", ""),
                    "source": source_name,
                    "source_type": "rss",
                    "timestamp": timestamp,
                    "raw_data": None
                }

                if news_item["headline"]:
                    news_items.append(news_item)

        except Exception as e:
            logger.error(f"Error parsing RSS {source_name}: {e}")

        return news_items

    def _fetch_finnhub(self) -> List[Dict]:
        """Fetch market news from Finnhub API."""
        news_items = []

        try:
            # General market news
            url = f"{self.finnhub_base}/news"
            params = {
                "category": "general",
                "token": FINNHUB_API_KEY
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data[:20]:
                timestamp = datetime.fromtimestamp(item.get("datetime", 0))

                # Skip old news
                if datetime.now() - timestamp > timedelta(hours=24):
                    continue

                news_item = {
                    "id": self._generate_id(item.get("headline", "")),
                    "headline": item.get("headline", "").strip(),
                    "summary": item.get("summary", "")[:500],
                    "url": item.get("url", ""),
                    "source": item.get("source", "finnhub"),
                    "source_type": "api",
                    "timestamp": timestamp,
                    "raw_data": {
                        "category": item.get("category"),
                        "related": item.get("related"),
                    }
                }

                if news_item["headline"]:
                    news_items.append(news_item)

        except Exception as e:
            logger.error(f"Finnhub API error: {e}")

        return news_items

    def fetch_india_specific(self) -> List[Dict]:
        """Fetch India-focused news only."""
        india_sources = ["moneycontrol", "economic_times", "livemint"]
        all_news = []

        for source in india_sources:
            if source in RSS_FEEDS:
                try:
                    news = self._fetch_rss(source, RSS_FEEDS[source])
                    all_news.extend(news)
                except Exception as e:
                    logger.warning(f"India RSS fetch failed for {source}: {e}")

        return sorted(all_news, key=lambda x: x["timestamp"], reverse=True)

    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text."""
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _deduplicate(self, news_items: List[Dict]) -> List[Dict]:
        """Remove duplicate news items."""
        unique = []
        seen_headlines = set()

        for item in news_items:
            # Normalize headline for comparison
            normalized = item["headline"].lower().strip()

            # Skip if too similar to existing
            if normalized in seen_headlines:
                continue

            # Check for similar headlines (simple approach)
            is_duplicate = False
            for seen in seen_headlines:
                if self._is_similar(normalized, seen):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(item)
                seen_headlines.add(normalized)

        return unique

    def _is_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are similar."""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        total = min(len(words1), len(words2))

        return (overlap / total) >= threshold if total > 0 else False


# Convenience function
def fetch_latest_news() -> List[Dict]:
    """Fetch latest news from all sources."""
    fetcher = NewsFetcher()
    return fetcher.fetch_all()


def fetch_india_news() -> List[Dict]:
    """Fetch India-specific news."""
    fetcher = NewsFetcher()
    return fetcher.fetch_india_specific()
