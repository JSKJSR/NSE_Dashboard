# Real-Time Market Intelligence Widget - Architecture Plan

## Executive Summary

Build a Bloomberg-style market intelligence system optimized for personal/semi-professional trading, integrated into your existing NSE Bias Dashboard. The system ingests multi-source data, classifies events, scores urgency, and surfaces actionable alerts.

---

## 1. End-to-End Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ News APIs│  │ X/Twitter│  │  Macro   │  │ Geopolitical│ │ Central │      │
│  │(Reuters, │  │  Feeds   │  │ Calendar │  │   Feeds   │  │  Banks  │      │
│  │Bloomberg)│  │          │  │          │  │           │  │  Feeds  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └────┬────┘      │
│       │             │             │              │              │           │
│       └─────────────┴─────────────┴──────────────┴──────────────┘           │
│                                   │                                          │
│                                   ▼                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                         EVENT PROCESSING LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  Raw Ingestion  │───▶│  NLP Classifier │───▶│  Event Enricher │         │
│  │  (Dedup, Clean) │    │  (Category/Type)│    │  (Context Add)  │         │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘         │
│                                                          │                   │
│                                                          ▼                   │
│                              ┌─────────────────────────────────────┐        │
│                              │      PRIORITY SCORING ENGINE        │        │
│                              │  ┌─────────┐ ┌─────────┐ ┌────────┐│        │
│                              │  │ Urgency │ │ Impact  │ │Credibility│       │
│                              │  │  Score  │ │  Score  │ │  Score ││        │
│                              │  └─────────┘ └─────────┘ └────────┘│        │
│                              └──────────────────┬──────────────────┘        │
│                                                 │                            │
├─────────────────────────────────────────────────┼────────────────────────────┤
│                         STORAGE & STATE LAYER   │                            │
├─────────────────────────────────────────────────┼────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐     │                            │
│  │  SQLite/Redis   │    │  Event History  │◀────┘                            │
│  │  (Fast Cache)   │    │  (Last 7 days)  │                                  │
│  └─────────────────┘    └─────────────────┘                                  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           ALERTING LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  Dashboard UI   │    │  Push Notifs    │    │  Sound Alerts   │         │
│  │  (Streamlit)    │    │  (Telegram/SMS) │    │  (Critical)     │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Recommended Data Sources & APIs

### 2.1 Financial News APIs

| Source | API | Cost | Latency | Best For |
|--------|-----|------|---------|----------|
| **NewsAPI.org** | REST | Free tier (100/day) | ~30s | General news aggregation |
| **Finnhub** | REST/WebSocket | Free tier available | ~5s | Market news, earnings |
| **Alpha Vantage** | REST | Free (5/min) | ~60s | News sentiment |
| **Benzinga** | REST | $99/mo | ~2s | Breaking market news |
| **Polygon.io** | REST/WebSocket | $29/mo | ~1s | US market news |
| **EODHD** | REST | $20/mo | ~30s | Global markets |

**Recommendation for India focus:**
- **Primary:** Finnhub (free, good coverage) + custom RSS feeds
- **Secondary:** NewsAPI for broader coverage
- **India-specific:** MoneyControl RSS, Economic Times RSS, LiveMint RSS

### 2.2 Macro Calendar & Economic Data

| Source | Coverage | Cost | Notes |
|--------|----------|------|-------|
| **Investing.com Calendar** | Global | Free (scrape) | Best free option |
| **TradingEconomics** | Global | $49/mo API | Comprehensive |
| **Finnhub Economic Calendar** | US/EU | Free tier | Good for majors |
| **RBI Calendar** | India | Free (manual) | Rate decisions |
| **MOSPI** | India | Free | GDP, CPI, IIP |

**Key Events to Track:**
```python
CRITICAL_EVENTS = {
    "india": ["RBI_RATE", "CPI_IN", "GDP_IN", "IIP", "PMI_IN", "TRADE_BALANCE_IN"],
    "us": ["FOMC", "NFP", "CPI_US", "GDP_US", "JOBLESS_CLAIMS", "ISM_PMI"],
    "global": ["ECB_RATE", "BOJ_RATE", "BOE_RATE", "CHINA_PMI", "OPEC_MEETING"]
}
```

### 2.3 X (Twitter) / Social Media

| Approach | Cost | Speed | Reliability |
|----------|------|-------|-------------|
| **X API v2 (Basic)** | $100/mo | Real-time | High (rate limited) |
| **X API v2 (Pro)** | $5000/mo | Real-time | High |
| **Nitter instances** | Free | ~1-5min delay | Medium (unstable) |
| **Social Searcher** | $4/mo | ~5min | Medium |

**Critical Accounts to Monitor:**
```python
PRIORITY_ACCOUNTS = {
    "tier_1_critical": [  # Immediate market impact
        "@RBI",              # Reserve Bank of India
        "@FinMinIndia",      # Finance Ministry
        "@nsaborlaw",        # Walter Bloomberg (fastest news)
        "@DeItaone",         # Market headlines
        "@FirstSquawk",      # Breaking news
        "@FedGov",           # Federal Reserve
    ],
    "tier_2_important": [  # High impact, verify first
        "@PMOIndia",
        "@ABORLAW",
        "@zaborowlaw",
        "@markets",
        "@business",
        "@ReutersBiz",
    ],
    "tier_3_context": [  # Background/analysis
        "@EPICIndia",
        "@IaborLaw",
        "@MacroAlf",
        "@NorthmanTrader",
    ]
}
```

### 2.4 Geopolitical Intelligence

| Source | Focus | Access |
|--------|-------|--------|
| **GDELT Project** | Global events database | Free API |
| **ACLED** | Conflict data | Free (academic) |
| **Reuters/AP RSS** | Breaking geopolitical | Free RSS |
| **Janes (IHS Markit)** | Defense/security | Expensive |
| **Stratfor** | Geopolitical analysis | $300/yr |

**Free Alternative Stack:**
- GDELT API for event detection
- Reuters World RSS for breaking news
- Custom keyword monitoring on news APIs

---

## 3. Event Classification & Priority Scoring System

### 3.1 Event Taxonomy

```python
EVENT_CATEGORIES = {
    "MONETARY_POLICY": {
        "subtypes": ["RATE_DECISION", "EMERGENCY_CUT", "QE_ANNOUNCEMENT", "FORWARD_GUIDANCE"],
        "base_impact": 9,
        "markets_affected": ["equity", "bond", "currency", "all"]
    },
    "MACRO_DATA": {
        "subtypes": ["CPI", "GDP", "NFP", "PMI", "TRADE_BALANCE", "INDUSTRIAL_PRODUCTION"],
        "base_impact": 7,
        "markets_affected": ["equity", "bond", "currency"]
    },
    "GEOPOLITICAL": {
        "subtypes": ["WAR_ESCALATION", "SANCTIONS", "TRADE_WAR", "ELECTION", "COUP", "TERROR"],
        "base_impact": 8,
        "markets_affected": ["equity", "commodity", "currency", "safe_haven"]
    },
    "CORPORATE": {
        "subtypes": ["EARNINGS_SURPRISE", "GUIDANCE_CHANGE", "M&A", "BANKRUPTCY", "FRAUD"],
        "base_impact": 5,
        "markets_affected": ["equity_single", "sector"]
    },
    "MARKET_STRUCTURE": {
        "subtypes": ["CIRCUIT_BREAKER", "EXCHANGE_HALT", "LIQUIDITY_CRISIS", "FLASH_CRASH"],
        "base_impact": 10,
        "markets_affected": ["all"]
    },
    "REGULATORY": {
        "subtypes": ["NEW_REGULATION", "TAX_CHANGE", "SEBI_ACTION", "FII_LIMIT_CHANGE"],
        "base_impact": 6,
        "markets_affected": ["equity", "sector"]
    }
}
```

### 3.2 Priority Scoring Formula

```python
def calculate_priority_score(event):
    """
    Final Score = (Impact × Urgency × Credibility) + Relevance Bonus
    Scale: 0-100
    """

    # 1. IMPACT SCORE (0-10)
    base_impact = EVENT_CATEGORIES[event.category]["base_impact"]
    surprise_factor = calculate_surprise(event)  # How unexpected (0-2x multiplier)
    magnitude_factor = calculate_magnitude(event)  # Size of move/change (0-2x)
    impact_score = min(10, base_impact * surprise_factor * magnitude_factor)

    # 2. URGENCY SCORE (0-10)
    time_sensitivity = get_time_sensitivity(event)  # Pre-market vs during hours
    decay_factor = calculate_time_decay(event.timestamp)  # Freshness
    urgency_score = time_sensitivity * decay_factor

    # 3. CREDIBILITY SCORE (0-10)
    source_tier = SOURCE_CREDIBILITY[event.source]  # 1=official, 0.5=news, 0.3=social
    verification_status = 1.0 if event.verified else 0.6
    credibility_score = source_tier * verification_status * 10

    # 4. RELEVANCE BONUS (0-20)
    portfolio_relevance = check_portfolio_match(event)  # Does it affect your holdings?
    india_relevance = 1.5 if event.affects_india else 1.0
    relevance_bonus = portfolio_relevance * india_relevance * 10

    # FINAL CALCULATION
    raw_score = (impact_score * urgency_score * credibility_score) / 100
    final_score = min(100, raw_score * 10 + relevance_bonus)

    return final_score

# Priority Thresholds
PRIORITY_LEVELS = {
    "CRITICAL": (80, 100),   # 🔴 Sound alert + push notification
    "HIGH": (60, 79),        # 🟠 Push notification + dashboard highlight
    "MEDIUM": (40, 59),      # 🟡 Dashboard alert
    "LOW": (20, 39),         # 🟢 Dashboard log
    "NOISE": (0, 19),        # ⚪ Archive only
}
```

### 3.3 Surprise Detection Logic

```python
def calculate_surprise(event):
    """Detect if macro data or event is a surprise vs expectations."""

    if event.category == "MACRO_DATA":
        # Compare actual vs consensus
        if event.actual is None or event.consensus is None:
            return 1.0

        deviation = abs(event.actual - event.consensus)
        historical_std = get_historical_std(event.subtype)
        z_score = deviation / historical_std if historical_std > 0 else 0

        # Surprise multiplier based on z-score
        if z_score > 3:
            return 2.0  # Massive surprise
        elif z_score > 2:
            return 1.7  # Big surprise
        elif z_score > 1:
            return 1.3  # Moderate surprise
        else:
            return 1.0  # In-line

    elif event.category == "MONETARY_POLICY":
        # Rate decisions: compare vs market pricing
        if event.subtype == "RATE_DECISION":
            implied_rate = get_market_implied_rate(event.currency)
            actual_rate = event.rate_change
            if actual_rate != implied_rate:
                return 2.0 if abs(actual_rate - implied_rate) > 25 else 1.5

        # Emergency actions always maximum surprise
        if event.subtype == "EMERGENCY_CUT":
            return 2.0

    return 1.0

# Macro Surprise Thresholds (India-specific)
MACRO_THRESHOLDS = {
    "CPI_IN": {"low": 0.2, "medium": 0.5, "high": 1.0},  # % deviation
    "GDP_IN": {"low": 0.3, "medium": 0.7, "high": 1.5},
    "RBI_RATE": {"low": 0, "medium": 25, "high": 50},     # bps
    "NFP": {"low": 50000, "medium": 100000, "high": 200000},
    "CPI_US": {"low": 0.1, "medium": 0.3, "high": 0.5},
}
```

---

## 4. Rate Change & Macro Surprise Detection

### 4.1 Central Bank Rate Decision Parser

```python
class RateDecisionDetector:
    """Detect and parse central bank rate decisions."""

    RATE_KEYWORDS = {
        "hike": ["hike", "raise", "increase", "tighten", "hawkish"],
        "cut": ["cut", "lower", "reduce", "ease", "dovish"],
        "hold": ["hold", "unchanged", "maintain", "pause", "steady"],
        "emergency": ["emergency", "unscheduled", "extraordinary", "special meeting"]
    }

    CENTRAL_BANKS = {
        "RBI": {"currency": "INR", "pattern": r"repo rate.*?(\d+\.?\d*)\s*%"},
        "FED": {"currency": "USD", "pattern": r"federal funds.*?(\d+\.?\d*)\s*%"},
        "ECB": {"currency": "EUR", "pattern": r"deposit rate.*?(\d+\.?\d*)\s*%"},
        "BOE": {"currency": "GBP", "pattern": r"bank rate.*?(\d+\.?\d*)\s*%"},
    }

    def parse_rate_decision(self, text, source):
        """Extract rate decision from news text."""
        text_lower = text.lower()

        # Detect central bank
        bank = None
        for cb, info in self.CENTRAL_BANKS.items():
            if cb.lower() in text_lower or info["currency"].lower() in text_lower:
                bank = cb
                break

        if not bank:
            return None

        # Detect action type
        action = "unknown"
        for action_type, keywords in self.RATE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                action = action_type
                break

        # Extract rate value
        import re
        pattern = self.CENTRAL_BANKS[bank]["pattern"]
        match = re.search(pattern, text_lower)
        rate = float(match.group(1)) if match else None

        # Extract basis points change
        bps_match = re.search(r"(\d+)\s*(?:basis points|bps|bp)", text_lower)
        bps_change = int(bps_match.group(1)) if bps_match else None

        return {
            "central_bank": bank,
            "action": action,
            "rate": rate,
            "bps_change": bps_change,
            "is_emergency": action == "emergency",
            "raw_text": text[:200]
        }
```

### 4.2 Macro Data Surprise Scorer

```python
class MacroSurpriseScorer:
    """Score macro data releases vs expectations."""

    def __init__(self):
        self.expectations = {}  # Load from calendar API
        self.historical_data = {}  # For std calculation

    def score_release(self, indicator, actual, country="IN"):
        """
        Returns surprise score and market implication.
        Score: -2 (big miss) to +2 (big beat)
        """
        key = f"{indicator}_{country}"

        if key not in self.expectations:
            return {"score": 0, "implication": "unknown"}

        consensus = self.expectations[key]["consensus"]
        previous = self.expectations[key]["previous"]
        std = self.historical_data.get(key, {}).get("std", 1)

        # Calculate deviation
        deviation = actual - consensus
        z_score = deviation / std if std > 0 else 0

        # Determine direction based on indicator type
        higher_is_better = indicator in ["GDP", "PMI", "NFP", "INDUSTRIAL_PROD"]

        # Score mapping
        if z_score > 2:
            score = 2 if higher_is_better else -2
        elif z_score > 1:
            score = 1 if higher_is_better else -1
        elif z_score < -2:
            score = -2 if higher_is_better else 2
        elif z_score < -1:
            score = -1 if higher_is_better else 1
        else:
            score = 0

        # Market implication
        implications = {
            2: "Strong bullish - expect rally",
            1: "Mildly bullish - positive bias",
            0: "Neutral - in-line with expectations",
            -1: "Mildly bearish - negative bias",
            -2: "Strong bearish - expect selloff"
        }

        return {
            "score": score,
            "z_score": round(z_score, 2),
            "deviation": round(deviation, 2),
            "implication": implications[score],
            "actual": actual,
            "consensus": consensus,
            "previous": previous
        }
```

---

## 5. Geopolitical Risk Event Detection

### 5.1 Risk Event Classifier

```python
GEOPOLITICAL_PATTERNS = {
    "WAR_ESCALATION": {
        "keywords": ["military strike", "invasion", "troops deployed", "missile",
                    "bombing", "declaration of war", "martial law"],
        "entities": ["russia", "ukraine", "china", "taiwan", "israel", "iran",
                    "north korea", "pakistan", "india border"],
        "impact": "HIGH",
        "affected_assets": ["safe_haven_up", "oil_up", "equity_down"]
    },
    "SANCTIONS": {
        "keywords": ["sanctions", "embargo", "trade ban", "asset freeze",
                    "blacklist", "export controls"],
        "entities": ["russia", "china", "iran", "us treasury", "ofac"],
        "impact": "MEDIUM-HIGH",
        "affected_assets": ["sector_specific", "currency"]
    },
    "TAIWAN_CHINA": {
        "keywords": ["taiwan strait", "chinese military", "pla", "blockade",
                    "airspace violation", "median line"],
        "entities": ["taiwan", "tsmc", "semiconductors"],
        "impact": "CRITICAL",
        "affected_assets": ["tech_down", "safe_haven_up", "chip_stocks"]
    },
    "SHIPPING_DISRUPTION": {
        "keywords": ["suez", "panama canal", "strait of hormuz", "red sea",
                    "shipping route", "houthi", "piracy"],
        "entities": ["container", "freight", "tanker"],
        "impact": "MEDIUM",
        "affected_assets": ["shipping_up", "oil_up", "inflation_concern"]
    },
    "TRADE_WAR": {
        "keywords": ["tariff", "trade war", "import duty", "retaliatory",
                    "wto dispute", "dumping"],
        "entities": ["us", "china", "eu", "india"],
        "impact": "MEDIUM",
        "affected_assets": ["sector_specific", "exporter_stocks"]
    }
}

def classify_geopolitical_event(text, entities):
    """Classify geopolitical event and assess market impact."""
    text_lower = text.lower()

    matches = []
    for event_type, config in GEOPOLITICAL_PATTERNS.items():
        keyword_hits = sum(1 for kw in config["keywords"] if kw in text_lower)
        entity_hits = sum(1 for ent in config["entities"] if ent in text_lower)

        if keyword_hits >= 2 or (keyword_hits >= 1 and entity_hits >= 1):
            matches.append({
                "type": event_type,
                "confidence": min(1.0, (keyword_hits + entity_hits) / 5),
                "impact": config["impact"],
                "affected_assets": config["affected_assets"]
            })

    return sorted(matches, key=lambda x: x["confidence"], reverse=True)
```

---

## 6. Social Media Signal Processing

### 6.0 Sentiment Analysis Libraries (Open Source)

For analyzing social media sentiment, use a **dual-layer approach** combining speed and accuracy:

#### Recommended Libraries

| Library | Best For | Speed | Accuracy | Install |
|---------|----------|-------|----------|---------|
| **VADER** | Real-time tweets, emojis, slang | ⚡ Fast | Good | `pip install vaderSentiment` |
| **FinBERT** | Financial news/text | 🐢 Slow | Excellent | `pip install transformers torch` |
| **TweetNLP** | Twitter-specific analysis | Medium | Very Good | `pip install tweetnlp` |
| **TextBlob** | Quick prototyping | ⚡ Fast | Basic | `pip install textblob` |

#### Implementation Strategy

```python
# sentiment_analyzer.py

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline

class DualSentimentAnalyzer:
    """
    Two-tier sentiment analysis:
    - VADER for speed (all incoming signals)
    - FinBERT for accuracy (high-priority financial content)
    """

    def __init__(self):
        # Fast analyzer for real-time processing
        self.vader = SentimentIntensityAnalyzer()

        # Accurate analyzer for financial text (lazy load)
        self._finbert = None

    @property
    def finbert(self):
        """Lazy load FinBERT to save memory."""
        if self._finbert is None:
            self._finbert = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert"
            )
        return self._finbert

    def analyze_fast(self, text):
        """
        Quick VADER analysis for real-time feed.
        Returns: score from -1 (negative) to +1 (positive)
        """
        scores = self.vader.polarity_scores(text)
        return {
            "compound": scores["compound"],  # -1 to +1
            "label": self._compound_to_label(scores["compound"]),
            "method": "vader"
        }

    def analyze_accurate(self, text):
        """
        FinBERT analysis for critical/financial content.
        Use sparingly due to latency.
        """
        result = self.finbert(text[:512])[0]  # FinBERT max 512 tokens

        # Convert FinBERT output to normalized score
        label = result["label"].lower()
        confidence = result["score"]

        if label == "positive":
            score = confidence
        elif label == "negative":
            score = -confidence
        else:
            score = 0

        return {
            "compound": round(score, 3),
            "label": label,
            "confidence": round(confidence, 3),
            "method": "finbert"
        }

    def analyze_smart(self, text, is_financial=True, is_critical=False):
        """
        Smart routing: VADER first, FinBERT for verification.
        """
        # Always run fast VADER first
        vader_result = self.analyze_fast(text)

        # Use FinBERT for financial content OR high-magnitude signals
        needs_verification = (
            is_critical or
            (is_financial and abs(vader_result["compound"]) > 0.5)
        )

        if needs_verification:
            finbert_result = self.analyze_accurate(text)
            return {
                "compound": finbert_result["compound"],
                "label": finbert_result["label"],
                "confidence": finbert_result["confidence"],
                "vader_score": vader_result["compound"],
                "method": "finbert_verified"
            }

        return vader_result

    def _compound_to_label(self, compound):
        """Convert VADER compound score to label."""
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        return "neutral"


# Usage Examples
analyzer = DualSentimentAnalyzer()

# Real-time tweet processing (fast)
tweet = "NIFTY crashes 500 points! 📉😱 Markets in panic"
result = analyzer.analyze_fast(tweet)
# {'compound': -0.8, 'label': 'negative', 'method': 'vader'}

# Financial news verification (accurate)
news = "RBI maintains repo rate at 6.5%, signals accommodative stance"
result = analyzer.analyze_smart(news, is_financial=True)
# {'compound': 0.45, 'label': 'positive', 'confidence': 0.89, 'method': 'finbert_verified'}

# Critical alert (always verify)
alert = "BREAKING: Emergency rate cut by Federal Reserve"
result = analyzer.analyze_smart(alert, is_critical=True)
```

#### TweetNLP for Twitter-Specific Analysis

```python
# For comprehensive tweet analysis (sentiment + emotion + topics)
import tweetnlp

class TweetAnalyzer:
    """Twitter-optimized analysis using TweetNLP."""

    def __init__(self):
        self.sentiment_model = tweetnlp.Sentiment()
        self.emotion_model = tweetnlp.Emotion()
        self.topic_model = tweetnlp.TopicClassification()

    def analyze_tweet(self, text):
        """Full tweet analysis."""
        return {
            "sentiment": self.sentiment_model.sentiment(text),
            # {'label': 'positive', 'probability': 0.85}

            "emotion": self.emotion_model.emotion(text),
            # {'label': 'fear', 'probability': 0.72}

            "topic": self.topic_model.topic(text),
            # {'label': 'business_&_entrepreneurs', 'probability': 0.65}
        }

# Usage
tweet_analyzer = TweetAnalyzer()
result = tweet_analyzer.analyze_tweet("Markets tanking on war fears! 😨")
# sentiment: negative, emotion: fear, topic: business
```

#### Market-Specific Sentiment Rules

```python
# Financial sentiment modifiers
MARKET_SENTIMENT_RULES = {
    # Bullish indicators
    "bullish_keywords": [
        "rally", "surge", "breakout", "all-time high", "ATH",
        "buying opportunity", "accumulate", "upgrade", "beat estimates"
    ],

    # Bearish indicators
    "bearish_keywords": [
        "crash", "plunge", "breakdown", "capitulation", "selloff",
        "downgrade", "miss estimates", "warning", "crisis"
    ],

    # High urgency modifiers
    "urgency_keywords": [
        "breaking", "just in", "alert", "emergency", "flash",
        "halt", "circuit breaker", "limit down", "limit up"
    ],

    # Uncertainty modifiers (reduce confidence)
    "uncertainty_keywords": [
        "rumor", "unconfirmed", "speculation", "may", "might",
        "possibly", "sources say", "allegedly"
    ]
}

def adjust_sentiment_for_markets(base_sentiment, text):
    """Adjust sentiment score based on market-specific keywords."""
    text_lower = text.lower()

    adjustment = 0
    confidence_modifier = 1.0

    # Check bullish keywords
    bullish_hits = sum(1 for kw in MARKET_SENTIMENT_RULES["bullish_keywords"]
                       if kw in text_lower)
    adjustment += bullish_hits * 0.1

    # Check bearish keywords
    bearish_hits = sum(1 for kw in MARKET_SENTIMENT_RULES["bearish_keywords"]
                       if kw in text_lower)
    adjustment -= bearish_hits * 0.1

    # Check uncertainty (reduce confidence)
    uncertainty_hits = sum(1 for kw in MARKET_SENTIMENT_RULES["uncertainty_keywords"]
                          if kw in text_lower)
    confidence_modifier -= uncertainty_hits * 0.15

    # Apply adjustments
    adjusted_score = max(-1, min(1, base_sentiment + adjustment))

    return {
        "score": round(adjusted_score, 3),
        "confidence_modifier": round(max(0.3, confidence_modifier), 2),
        "bullish_signals": bullish_hits,
        "bearish_signals": bearish_hits,
        "uncertainty_flags": uncertainty_hits
    }
```

#### Requirements for Sentiment Module

```txt
# requirements-sentiment.txt
vaderSentiment>=3.3.2
transformers>=4.30.0
torch>=2.0.0
tweetnlp>=0.2.0
textblob>=0.17.1
```

### 6.1 Credibility-Weighted Tweet Processor

```python
class TweetProcessor:
    """Process and weight tweets by credibility."""

    SOURCE_CREDIBILITY = {
        # Tier 1: Official accounts (weight: 1.0)
        "@RBI": 1.0,
        "@FinMinIndia": 1.0,
        "@ABORLAW": 0.95,
        "@FedGov": 1.0,

        # Tier 2: Fast news accounts (weight: 0.8-0.9)
        "@DeItaone": 0.9,
        "@FirstSquawk": 0.85,
        "@LiveSquawk": 0.85,
        "@Newsquawk": 0.85,

        # Tier 3: News organizations (weight: 0.7-0.8)
        "@Reuters": 0.8,
        "@Bloomberg": 0.8,
        "@ABORLAW": 0.75,

        # Tier 4: Analysts/Commentators (weight: 0.4-0.6)
        "@MacroAlf": 0.5,
        "@NorthmanTrader": 0.45,

        # Unknown accounts
        "default": 0.3
    }

    def process_tweet(self, tweet):
        """Convert tweet to structured event with credibility score."""

        # Get base credibility
        author = f"@{tweet['author_username']}"
        credibility = self.SOURCE_CREDIBILITY.get(author,
                      self.SOURCE_CREDIBILITY["default"])

        # Boost if verified or has high engagement
        if tweet.get("verified", False):
            credibility = min(1.0, credibility * 1.2)

        # Check for hedging language (reduces credibility)
        hedging_words = ["rumor", "unconfirmed", "reportedly", "sources say",
                        "may", "might", "could", "possibly"]
        if any(word in tweet["text"].lower() for word in hedging_words):
            credibility *= 0.7

        # Check for confirmation signals (increases credibility)
        confirm_words = ["confirmed", "official", "breaking", "just announced",
                        "statement:", "press release"]
        if any(word in tweet["text"].lower() for word in confirm_words):
            credibility = min(1.0, credibility * 1.3)

        return {
            "text": tweet["text"],
            "author": author,
            "timestamp": tweet["created_at"],
            "credibility": round(credibility, 2),
            "requires_verification": credibility < 0.7,
            "engagement": tweet.get("retweet_count", 0) + tweet.get("like_count", 0)
        }

    def deduplicate_events(self, events, time_window_minutes=5):
        """Remove duplicate events from multiple sources."""
        from difflib import SequenceMatcher

        unique_events = []
        for event in sorted(events, key=lambda x: x["credibility"], reverse=True):
            is_duplicate = False
            for existing in unique_events:
                # Check text similarity
                similarity = SequenceMatcher(None,
                    event["text"].lower(),
                    existing["text"].lower()
                ).ratio()

                # Check time proximity
                time_diff = abs((event["timestamp"] - existing["timestamp"]).seconds)

                if similarity > 0.7 and time_diff < time_window_minutes * 60:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_events.append(event)

        return unique_events
```

---

## 7. Dashboard Integration Design

### 7.1 UI Component Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXISTING NSE BIAS DASHBOARD                          │
├─────────────────────────────────────────────────────────────────────────┤
│  [Bias Score]  [Institutional]  [Global Markets]  [NIFTY Technical]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              🔔 MARKET INTELLIGENCE FEED                        │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ 🔴 CRITICAL ALERTS (Sound + Visual)                      │   │   │
│  │  │ ┌─────────────────────────────────────────────────────┐ │   │   │
│  │  │ │ 10:32 | RBI Emergency Rate Cut -50bps | 🏦 Official │ │   │   │
│  │  │ └─────────────────────────────────────────────────────┘ │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟠 HIGH PRIORITY                                         │   │   │
│  │  │ • 10:28 | US CPI +0.4% vs +0.2% exp | Bearish bonds     │   │   │
│  │  │ • 10:15 | Taiwan: China jets cross median line          │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟡 MEDIUM PRIORITY                                       │   │   │
│  │  │ • 10:05 | Adani Group: Rating downgrade by Moody's      │   │   │
│  │  │ • 09:45 | Oil: OPEC+ production cut speculation         │   │   │
│  │  │ • 09:30 | FII outflow continues: -2500 Cr preliminary   │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                 │   │
│  │  [Filter: All | Macro | Geopolitical | Corporate | Social]     │   │
│  │  [Time: Last 1h | 4h | Today | Week]                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────────────────┐  ┌────────────────────────────────┐   │
│  │   📅 UPCOMING EVENTS       │  │   📊 MARKET IMPACT TRACKER     │   │
│  │   Today:                   │  │   Last event impact:           │   │
│  │   • 14:00 RBI Minutes     │  │   "US CPI" → NIFTY -0.8%       │   │
│  │   • 18:30 US Jobless      │  │   "China news" → IT stocks -2% │   │
│  │   Tomorrow:               │  │                                 │   │
│  │   • 09:00 IN PMI          │  │   [View correlation analysis]  │   │
│  └────────────────────────────┘  └────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Streamlit Implementation Structure

```python
# New file: dashboard/components/market_intel.py

import streamlit as st
from datetime import datetime, timedelta

def render_market_intelligence_widget():
    """Render the market intelligence feed widget."""

    st.markdown("---")
    st.subheader("🔔 Market Intelligence Feed")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        category_filter = st.selectbox(
            "Category",
            ["All", "Macro", "Geopolitical", "Corporate", "Central Banks"],
            key="intel_category"
        )
    with col2:
        time_filter = st.selectbox(
            "Time Range",
            ["Last 1 hour", "Last 4 hours", "Today", "This Week"],
            key="intel_time"
        )
    with col3:
        if st.button("🔄 Refresh", key="intel_refresh"):
            st.cache_data.clear()

    # Fetch and display alerts
    alerts = get_filtered_alerts(category_filter, time_filter)

    # Critical alerts (with visual emphasis)
    critical = [a for a in alerts if a["priority"] == "CRITICAL"]
    if critical:
        st.error("🔴 **CRITICAL ALERTS**")
        for alert in critical:
            render_alert_card(alert, "critical")

    # High priority
    high = [a for a in alerts if a["priority"] == "HIGH"]
    if high:
        st.warning("🟠 **HIGH PRIORITY**")
        for alert in high[:5]:  # Limit display
            render_alert_card(alert, "high")

    # Medium priority (collapsed by default)
    medium = [a for a in alerts if a["priority"] == "MEDIUM"]
    if medium:
        with st.expander(f"🟡 MEDIUM PRIORITY ({len(medium)} events)"):
            for alert in medium[:10]:
                render_alert_card(alert, "medium")

    # Upcoming events sidebar
    render_upcoming_events()


def render_alert_card(alert, priority_level):
    """Render a single alert card."""

    # Color coding
    colors = {
        "critical": "#ff4444",
        "high": "#ff8c00",
        "medium": "#ffd700",
        "low": "#90EE90"
    }

    # Source badge
    source_emoji = {
        "official": "🏦",
        "news": "📰",
        "social": "🐦",
        "calendar": "📅"
    }

    emoji = source_emoji.get(alert.get("source_type", "news"), "📌")
    time_str = alert["timestamp"].strftime("%H:%M")

    st.markdown(f"""
    <div style="
        border-left: 4px solid {colors[priority_level]};
        padding: 8px 12px;
        margin: 4px 0;
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
    ">
        <span style="color: #888; font-size: 0.85em;">{time_str}</span> |
        <strong>{alert["headline"]}</strong>
        <span style="float: right;">{emoji} {alert.get("source", "")}</span>
        <br>
        <span style="color: #aaa; font-size: 0.85em;">{alert.get("implication", "")}</span>
    </div>
    """, unsafe_allow_html=True)


def render_upcoming_events():
    """Render upcoming economic events."""

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📅 Upcoming Events**")
        events = get_upcoming_events(days=2)
        for event in events[:5]:
            time_str = event["datetime"].strftime("%H:%M")
            importance = "🔴" if event["importance"] == "high" else "🟡"
            st.markdown(f"{importance} {time_str} - {event['name']}")

    with col2:
        st.markdown("**📊 Recent Event Impact**")
        impacts = get_recent_event_impacts()
        for impact in impacts[:3]:
            direction = "📈" if impact["market_move"] > 0 else "📉"
            st.markdown(f"{direction} {impact['event']}: NIFTY {impact['market_move']:+.1f}%")
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up data ingestion for Finnhub news API
- [ ] Create RSS feed parser for Indian financial news
- [ ] Build basic event classification (keyword-based)
- [ ] Create SQLite table for events
- [ ] Basic Streamlit widget showing latest headlines

### Phase 2: Intelligence Layer (Week 3-4)
- [ ] Implement priority scoring engine
- [ ] Add macro calendar integration (Investing.com scraper)
- [ ] Build rate decision parser
- [ ] Create macro surprise scorer
- [ ] Add credibility weighting

### Phase 3: Social & Geopolitical (Week 5-6)
- [ ] Integrate X API (or Nitter fallback)
- [ ] Implement tweet processor with deduplication
- [ ] Add geopolitical event classifier
- [ ] Build GDELT integration for conflict monitoring

### Phase 4: Alerting & Polish (Week 7-8)
- [ ] Implement push notifications (Telegram bot)
- [ ] Add sound alerts for critical events
- [ ] Create event impact tracker
- [ ] Performance optimization & caching
- [ ] User preference settings

---

## 9. Estimated Costs (Monthly)

| Component | Free Tier | Recommended | Premium |
|-----------|-----------|-------------|---------|
| News API | Finnhub free | $0 | Benzinga $99 |
| Social Media | Nitter (unstable) | X Basic $100 | X Pro $5000 |
| Macro Calendar | Scraping | $0 | TradingEconomics $49 |
| Geopolitical | GDELT free | $0 | Stratfor $25 |
| Push Notifications | Telegram free | $0 | Twilio $20 |
| **TOTAL** | **$0** | **$100** | **$5,193** |

**Recommendation:** Start with the free tier ($0), then upgrade to X Basic ($100/mo) once validated.

---

## 10. File Structure

```
NSE_Dashboard/
├── intelligence/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── news_fetcher.py       # Finnhub, RSS feeds
│   │   ├── social_fetcher.py     # X/Twitter integration
│   │   ├── calendar_fetcher.py   # Macro calendar
│   │   └── geopolitical_fetcher.py
│   ├── processing/
│   │   ├── classifier.py         # Event classification
│   │   ├── scorer.py             # Priority scoring
│   │   ├── rate_parser.py        # Central bank decisions
│   │   ├── macro_scorer.py       # Macro surprise detection
│   │   └── deduplicator.py       # Cross-source dedup
│   ├── alerting/
│   │   ├── notifier.py           # Push notifications
│   │   └── sound_alerts.py       # Audio alerts
│   └── storage/
│       └── events_db.py          # Event storage
├── dashboard/
│   ├── app.py                    # Main dashboard (existing)
│   └── components/
│       └── market_intel.py       # Intelligence widget
└── config/
    └── intel_settings.py         # API keys, thresholds
```

---

## Summary

This architecture provides:

1. **Multi-source ingestion** - News APIs, social media, macro calendars, geopolitical feeds
2. **Intelligent classification** - NLP-based event categorization with market impact mapping
3. **Priority scoring** - Impact × Urgency × Credibility formula to filter noise
4. **Macro surprise detection** - Z-score based comparison vs consensus
5. **Rate decision parsing** - Structured extraction from central bank announcements
6. **Credibility weighting** - Source-based trust scores for social media
7. **Clean UI integration** - Streamlit widget with priority-based visual hierarchy
8. **Scalable cost structure** - Start free, upgrade as needed

The system is designed to surface **actionable intelligence** rather than raw headlines, giving you a trading edge similar to Bloomberg terminals but optimized for a personal setup.
