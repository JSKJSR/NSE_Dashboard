"""
Event Classifier Module
MVP Version - Classifies news events and calculates priority scores
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from intelligence.config import EVENT_CATEGORIES, URGENCY_MODIFIERS, PRIORITY_LEVELS
from intelligence.sentiment import analyze_sentiment

logger = logging.getLogger(__name__)


class EventClassifier:
    """
    Classifies market events and calculates priority scores.

    Priority Formula: (Base Priority × Urgency Multiplier) + Sentiment Boost
    """

    def __init__(self):
        self.categories = EVENT_CATEGORIES
        self.urgency_modifiers = URGENCY_MODIFIERS

    def classify(self, news_item: Dict) -> Dict:
        """
        Classify a news item and calculate its priority.

        Args:
            news_item: Dictionary with headline, summary, source, timestamp

        Returns:
            Classified event with category, priority, and metadata
        """
        headline = news_item.get("headline", "")
        summary = news_item.get("summary", "")
        full_text = f"{headline} {summary}".lower()

        # 1. Determine category
        category, category_matches = self._detect_category(full_text)

        # 2. Get base priority from category
        base_priority = self._get_base_priority(category)

        # 3. Calculate urgency multiplier
        urgency_level, urgency_multiplier = self._detect_urgency(full_text)

        # 4. Get sentiment analysis
        sentiment = analyze_sentiment(headline, fast=True)

        # 5. Calculate sentiment boost (strong sentiment = more important)
        sentiment_boost = abs(sentiment["score"]) * 10  # Max +10 points

        # 6. Calculate final priority
        priority = min(100, (base_priority * urgency_multiplier) + sentiment_boost)

        # 7. Determine priority level
        priority_level = self._get_priority_level(priority)

        return {
            "id": news_item.get("id"),
            "headline": headline,
            "summary": news_item.get("summary", ""),
            "url": news_item.get("url", ""),
            "source": news_item.get("source", "unknown"),
            "timestamp": news_item.get("timestamp", datetime.now()),
            "category": category,
            "category_matches": category_matches,
            "priority": round(priority, 1),
            "priority_level": priority_level,
            "urgency": urgency_level,
            "sentiment": sentiment,
            "color": PRIORITY_LEVELS.get(priority_level, {}).get("color", "#808080"),
            "emoji": PRIORITY_LEVELS.get(priority_level, {}).get("emoji", "⚪")
        }

    def classify_batch(self, news_items: List[Dict]) -> List[Dict]:
        """Classify multiple news items."""
        classified = []
        for item in news_items:
            try:
                classified.append(self.classify(item))
            except Exception as e:
                logger.error(f"Classification error: {e}")
                continue

        # Sort by priority (highest first)
        return sorted(classified, key=lambda x: x["priority"], reverse=True)

    def _detect_category(self, text: str) -> Tuple[str, List[str]]:
        """
        Detect the most relevant category for the text.

        Returns:
            Tuple of (category_name, list of matched keywords)
        """
        best_category = "GENERAL"
        best_matches = []
        best_score = 0

        for category, config in self.categories.items():
            keywords = config.get("keywords", [])
            matches = [kw for kw in keywords if kw in text]

            if len(matches) > best_score:
                best_score = len(matches)
                best_category = category
                best_matches = matches

        return best_category, best_matches

    def _get_base_priority(self, category: str) -> float:
        """Get base priority score for a category."""
        if category in self.categories:
            return self.categories[category].get("base_priority", 50)
        return 30  # Default for GENERAL category

    def _detect_urgency(self, text: str) -> Tuple[str, float]:
        """
        Detect urgency level from text.

        Returns:
            Tuple of (urgency_level, multiplier)
        """
        for level, config in self.urgency_modifiers.items():
            keywords = config.get("keywords", [])
            if any(kw in text for kw in keywords):
                return level, config.get("multiplier", 1.0)

        return "normal", 1.0

    def _get_priority_level(self, priority: float) -> str:
        """Convert numeric priority to level name."""
        for level, config in PRIORITY_LEVELS.items():
            if priority >= config.get("min", 0):
                return level
        return "LOW"

    def filter_by_priority(self, events: List[Dict], min_level: str = "MEDIUM") -> List[Dict]:
        """Filter events by minimum priority level."""
        min_priority = PRIORITY_LEVELS.get(min_level, {}).get("min", 0)
        return [e for e in events if e["priority"] >= min_priority]

    def get_critical_events(self, events: List[Dict]) -> List[Dict]:
        """Get only critical priority events."""
        return self.filter_by_priority(events, "CRITICAL")

    def get_events_by_category(self, events: List[Dict], category: str) -> List[Dict]:
        """Get events of a specific category."""
        return [e for e in events if e["category"] == category]


class RateChangeDetector:
    """
    Specialized detector for central bank rate changes.
    These are critical market-moving events.
    """

    RATE_KEYWORDS = {
        "rbi": ["repo rate", "reverse repo", "crr", "slr", "rbi policy", "mpc decision"],
        "fed": ["fed rate", "fomc", "federal reserve", "fed decision", "basis points", "bps"],
        "ecb": ["ecb rate", "european central bank", "ecb decision"],
        "boe": ["bank of england", "boe rate"]
    }

    CHANGE_INDICATORS = {
        "hike": ["hike", "raise", "increase", "up", "higher", "tightening"],
        "cut": ["cut", "lower", "decrease", "down", "reduction", "easing"],
        "hold": ["hold", "unchanged", "maintain", "steady", "pause"]
    }

    def detect(self, text: str) -> Optional[Dict]:
        """
        Detect if text contains a rate change announcement.

        Returns:
            Dictionary with central bank, direction, and confidence if detected
        """
        text_lower = text.lower()

        # Check for central bank mention
        central_bank = None
        for bank, keywords in self.RATE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                central_bank = bank.upper()
                break

        if not central_bank:
            return None

        # Detect direction
        direction = None
        for change_type, indicators in self.CHANGE_INDICATORS.items():
            if any(ind in text_lower for ind in indicators):
                direction = change_type
                break

        if not direction:
            return None

        # Extract basis points if mentioned
        bps = self._extract_bps(text_lower)

        return {
            "central_bank": central_bank,
            "direction": direction,
            "basis_points": bps,
            "confidence": 0.9 if bps else 0.7
        }

    def _extract_bps(self, text: str) -> Optional[int]:
        """Extract basis points from text."""
        import re

        # Look for patterns like "25 bps", "25 basis points", "0.25%"
        bps_pattern = r'(\d+)\s*(?:bps|basis\s*points)'
        pct_pattern = r'(\d+\.?\d*)\s*%'

        bps_match = re.search(bps_pattern, text)
        if bps_match:
            return int(bps_match.group(1))

        pct_match = re.search(pct_pattern, text)
        if pct_match:
            return int(float(pct_match.group(1)) * 100)

        return None


class GeopoliticalDetector:
    """
    Detector for geopolitical events that may impact markets.
    """

    CONFLICT_KEYWORDS = [
        "war", "military", "attack", "missile", "troops", "invasion",
        "strike", "bombing", "conflict", "escalation"
    ]

    REGIONS_OF_CONCERN = [
        "ukraine", "russia", "taiwan", "china", "middle east", "israel",
        "iran", "north korea", "gaza", "red sea"
    ]

    SANCTION_KEYWORDS = [
        "sanctions", "embargo", "tariff", "trade war", "restrictions",
        "banned", "blacklist"
    ]

    def detect(self, text: str) -> Optional[Dict]:
        """
        Detect geopolitical events.

        Returns:
            Dictionary with event type, region, and severity if detected
        """
        text_lower = text.lower()

        # Check for conflict keywords
        conflict_matches = [kw for kw in self.CONFLICT_KEYWORDS if kw in text_lower]
        sanction_matches = [kw for kw in self.SANCTION_KEYWORDS if kw in text_lower]
        region_matches = [r for r in self.REGIONS_OF_CONCERN if r in text_lower]

        if not (conflict_matches or sanction_matches):
            return None

        # Determine event type
        if conflict_matches:
            event_type = "CONFLICT"
            severity = "HIGH" if len(conflict_matches) > 1 else "MEDIUM"
        else:
            event_type = "SANCTIONS"
            severity = "MEDIUM"

        return {
            "event_type": event_type,
            "regions": region_matches,
            "keywords_matched": conflict_matches + sanction_matches,
            "severity": severity
        }


# Convenience functions
_default_classifier = None


def get_classifier() -> EventClassifier:
    """Get or create default classifier instance."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = EventClassifier()
    return _default_classifier


def classify_news(news_items: List[Dict]) -> List[Dict]:
    """Classify a list of news items."""
    classifier = get_classifier()
    return classifier.classify_batch(news_items)


def detect_critical_events(news_items: List[Dict]) -> Dict:
    """
    Detect critical events (rate changes, geopolitical) from news.

    Returns:
        Dictionary with detected critical events
    """
    rate_detector = RateChangeDetector()
    geo_detector = GeopoliticalDetector()

    critical = {
        "rate_changes": [],
        "geopolitical": [],
        "count": 0
    }

    for item in news_items:
        text = f"{item.get('headline', '')} {item.get('summary', '')}"

        # Check for rate changes
        rate_event = rate_detector.detect(text)
        if rate_event:
            critical["rate_changes"].append({
                **rate_event,
                "headline": item.get("headline"),
                "source": item.get("source"),
                "timestamp": item.get("timestamp")
            })

        # Check for geopolitical events
        geo_event = geo_detector.detect(text)
        if geo_event:
            critical["geopolitical"].append({
                **geo_event,
                "headline": item.get("headline"),
                "source": item.get("source"),
                "timestamp": item.get("timestamp")
            })

    critical["count"] = len(critical["rate_changes"]) + len(critical["geopolitical"])
    return critical
