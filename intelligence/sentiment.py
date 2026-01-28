"""
Sentiment Analysis Module
MVP Version - VADER (fast) + optional FinBERT (accurate)
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Try to import VADER (lightweight, always available)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("VADER not installed. Run: pip install vaderSentiment")

# Try to import FinBERT (heavy, optional)
FINBERT_AVAILABLE = False
_finbert_pipeline = None

def _load_finbert():
    """Lazy load FinBERT model."""
    global FINBERT_AVAILABLE, _finbert_pipeline
    try:
        from transformers import pipeline
        _finbert_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert"
        )
        FINBERT_AVAILABLE = True
        logger.info("FinBERT loaded successfully")
    except Exception as e:
        logger.warning(f"FinBERT not available: {e}")
        FINBERT_AVAILABLE = False


class SentimentAnalyzer:
    """
    Dual-layer sentiment analysis.
    - VADER: Fast, good for social media, handles emojis
    - FinBERT: Accurate for financial text (optional, slower)
    """

    # Market-specific keyword modifiers
    BULLISH_KEYWORDS = [
        "rally", "surge", "breakout", "all-time high", "ath", "bullish",
        "buying opportunity", "accumulate", "upgrade", "beat", "strong buy",
        "outperform", "positive", "recovery", "gains"
    ]

    BEARISH_KEYWORDS = [
        "crash", "plunge", "breakdown", "selloff", "bearish", "capitulation",
        "downgrade", "miss", "warning", "crisis", "collapse", "losses",
        "underperform", "negative", "weakness", "decline"
    ]

    URGENCY_KEYWORDS = [
        "breaking", "just in", "alert", "emergency", "flash", "urgent",
        "developing", "confirmed", "official"
    ]

    def __init__(self, use_finbert: bool = False):
        """
        Initialize sentiment analyzer.

        Args:
            use_finbert: Whether to use FinBERT for verification (slower but more accurate)
        """
        self.use_finbert = use_finbert

        # Initialize VADER
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None

        # Load FinBERT if requested
        if use_finbert and not FINBERT_AVAILABLE:
            _load_finbert()

    def analyze(self, text: str, verify_critical: bool = True) -> Dict:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze
            verify_critical: If True, use FinBERT for high-magnitude signals

        Returns:
            Dictionary with sentiment scores and labels
        """
        if not text or not text.strip():
            return self._empty_result()

        # Start with VADER (fast)
        vader_result = self._analyze_vader(text)

        # Apply market-specific adjustments
        adjusted = self._apply_market_rules(vader_result, text)

        # Optionally verify with FinBERT for critical signals
        if (verify_critical and
            self.use_finbert and
            FINBERT_AVAILABLE and
            abs(adjusted["score"]) > 0.5):

            finbert_result = self._analyze_finbert(text)
            if finbert_result:
                # Combine scores (weighted average)
                combined_score = (adjusted["score"] * 0.4 + finbert_result["score"] * 0.6)
                return {
                    "score": round(combined_score, 3),
                    "label": self._score_to_label(combined_score),
                    "confidence": finbert_result.get("confidence", 0.5),
                    "vader_score": vader_result["score"],
                    "finbert_score": finbert_result["score"],
                    "method": "finbert_verified",
                    "market_signals": adjusted["market_signals"]
                }

        return adjusted

    def analyze_fast(self, text: str) -> Dict:
        """Quick VADER-only analysis for real-time processing."""
        if not text or not text.strip():
            return self._empty_result()

        result = self._analyze_vader(text)
        return self._apply_market_rules(result, text)

    def _analyze_vader(self, text: str) -> Dict:
        """Analyze with VADER."""
        if not self.vader:
            return self._empty_result()

        scores = self.vader.polarity_scores(text)
        compound = scores["compound"]

        return {
            "score": round(compound, 3),
            "label": self._score_to_label(compound),
            "confidence": abs(compound),
            "method": "vader",
            "details": {
                "positive": scores["pos"],
                "negative": scores["neg"],
                "neutral": scores["neu"]
            }
        }

    def _analyze_finbert(self, text: str) -> Optional[Dict]:
        """Analyze with FinBERT (if available)."""
        global _finbert_pipeline

        if not _finbert_pipeline:
            return None

        try:
            # FinBERT has 512 token limit
            truncated = text[:512]
            result = _finbert_pipeline(truncated)[0]

            label = result["label"].lower()
            confidence = result["score"]

            # Convert to -1 to +1 scale
            if label == "positive":
                score = confidence
            elif label == "negative":
                score = -confidence
            else:
                score = 0

            return {
                "score": round(score, 3),
                "label": label,
                "confidence": round(confidence, 3),
                "method": "finbert"
            }

        except Exception as e:
            logger.error(f"FinBERT analysis error: {e}")
            return None

    def _apply_market_rules(self, result: Dict, text: str) -> Dict:
        """Apply market-specific keyword adjustments."""
        text_lower = text.lower()

        # Count keyword hits
        bullish_hits = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bearish_hits = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)
        urgency_hits = sum(1 for kw in self.URGENCY_KEYWORDS if kw in text_lower)

        # Calculate adjustment
        adjustment = (bullish_hits - bearish_hits) * 0.1

        # Apply adjustment
        adjusted_score = max(-1, min(1, result["score"] + adjustment))

        return {
            "score": round(adjusted_score, 3),
            "label": self._score_to_label(adjusted_score),
            "confidence": result.get("confidence", 0.5),
            "method": result.get("method", "vader"),
            "market_signals": {
                "bullish_count": bullish_hits,
                "bearish_count": bearish_hits,
                "urgency_count": urgency_hits,
                "adjustment": round(adjustment, 3)
            }
        }

    def _score_to_label(self, score: float) -> str:
        """Convert numeric score to label."""
        if score >= 0.3:
            return "positive"
        elif score >= 0.05:
            return "slightly_positive"
        elif score <= -0.3:
            return "negative"
        elif score <= -0.05:
            return "slightly_negative"
        return "neutral"

    def _empty_result(self) -> Dict:
        """Return empty result for invalid input."""
        return {
            "score": 0,
            "label": "neutral",
            "confidence": 0,
            "method": "none",
            "market_signals": {}
        }


# Convenience functions
_default_analyzer = None

def get_analyzer(use_finbert: bool = False) -> SentimentAnalyzer:
    """Get or create default analyzer instance."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = SentimentAnalyzer(use_finbert=use_finbert)
    return _default_analyzer


def analyze_sentiment(text: str, fast: bool = True) -> Dict:
    """
    Quick sentiment analysis.

    Args:
        text: Text to analyze
        fast: If True, use VADER only. If False, may use FinBERT verification.
    """
    analyzer = get_analyzer(use_finbert=not fast)
    if fast:
        return analyzer.analyze_fast(text)
    return analyzer.analyze(text)


def get_market_sentiment(headlines: list) -> Dict:
    """
    Get aggregate sentiment from multiple headlines.

    Args:
        headlines: List of headline strings

    Returns:
        Aggregate sentiment analysis
    """
    if not headlines:
        return {"score": 0, "label": "neutral", "count": 0}

    analyzer = get_analyzer()
    scores = []

    for headline in headlines:
        result = analyzer.analyze_fast(headline)
        scores.append(result["score"])

    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "score": round(avg_score, 3),
        "label": analyzer._score_to_label(avg_score),
        "count": len(headlines),
        "positive_count": sum(1 for s in scores if s > 0.1),
        "negative_count": sum(1 for s in scores if s < -0.1),
        "neutral_count": sum(1 for s in scores if -0.1 <= s <= 0.1)
    }
