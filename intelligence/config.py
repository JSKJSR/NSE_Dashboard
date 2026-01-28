"""
Market Intelligence Configuration
MVP Version - Essential settings only
"""

from pathlib import Path

# === API KEYS (Set via environment variables) ===
import os

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")  # Free tier: 60 calls/min

# === RSS FEEDS (Free, No API Key Required) ===
RSS_FEEDS = {
    # Indian Financial News
    "moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "economic_times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "livemint": "https://www.livemint.com/rss/markets",

    # Global News
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "reuters_world": "https://feeds.reuters.com/Reuters/worldNews",

    # Central Banks
    "rbi_press": "https://rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=rss",
}

# === PRIORITY ACCOUNTS (Twitter/X - for future use) ===
PRIORITY_TWITTER_ACCOUNTS = [
    "RBI", "FinMinIndia", "nsaborlaw", "DeItaone",
    "FirstSquawk", "markets", "Reuters", "Bloomberg"
]

# === EVENT CLASSIFICATION ===
EVENT_CATEGORIES = {
    "MONETARY_POLICY": {
        "keywords": ["rate cut", "rate hike", "repo rate", "interest rate",
                    "rbi policy", "fed", "fomc", "monetary policy", "basis points", "bps"],
        "base_priority": 90,
        "color": "red"
    },
    "MACRO_DATA": {
        "keywords": ["gdp", "cpi", "inflation", "pmi", "iip", "employment",
                    "jobs report", "nonfarm", "trade deficit", "current account"],
        "base_priority": 75,
        "color": "orange"
    },
    "GEOPOLITICAL": {
        "keywords": ["war", "conflict", "sanctions", "military", "attack",
                    "taiwan", "china", "russia", "ukraine", "missile", "troops"],
        "base_priority": 85,
        "color": "red"
    },
    "MARKET_MOVE": {
        "keywords": ["crash", "rally", "surge", "plunge", "circuit breaker",
                    "all-time high", "record", "selloff", "correction"],
        "base_priority": 70,
        "color": "orange"
    },
    "CORPORATE": {
        "keywords": ["earnings", "quarterly results", "profit", "revenue",
                    "guidance", "merger", "acquisition", "buyback", "dividend"],
        "base_priority": 50,
        "color": "yellow"
    },
    "REGULATORY": {
        "keywords": ["sebi", "regulation", "compliance", "tax", "gst",
                    "policy change", "amendment", "notification"],
        "base_priority": 60,
        "color": "yellow"
    },
    "FII_DII": {
        "keywords": ["fii", "dii", "foreign institutional", "domestic institutional",
                    "fpi", "outflow", "inflow"],
        "base_priority": 65,
        "color": "orange"
    }
}

# === URGENCY KEYWORDS ===
URGENCY_MODIFIERS = {
    "critical": {
        "keywords": ["breaking", "just in", "alert", "emergency", "flash", "urgent"],
        "multiplier": 1.5
    },
    "high": {
        "keywords": ["developing", "update", "confirms", "announces", "official"],
        "multiplier": 1.2
    },
    "low": {
        "keywords": ["analysis", "opinion", "outlook", "forecast", "expects"],
        "multiplier": 0.7
    }
}

# === MARKET HOURS (IST) ===
MARKET_HOURS = {
    "pre_market": (7, 9),      # 7 AM - 9 AM IST
    "market_open": (9, 15),    # 9:15 AM - 3:30 PM IST
    "post_market": (15, 18),   # 3:30 PM - 6 PM IST
}

# === STORAGE ===
INTEL_DB_PATH = Path(__file__).parent.parent / "data" / "market_intel.db"

# === REFRESH INTERVALS ===
NEWS_REFRESH_SECONDS = 300  # 5 minutes
MAX_EVENTS_DISPLAY = 20
EVENT_RETENTION_DAYS = 7

# === PRIORITY THRESHOLDS ===
PRIORITY_LEVELS = {
    "CRITICAL": {"min": 80, "color": "#ff4444", "emoji": "🔴"},
    "HIGH": {"min": 60, "color": "#ff8c00", "emoji": "🟠"},
    "MEDIUM": {"min": 40, "color": "#ffd700", "emoji": "🟡"},
    "LOW": {"min": 0, "color": "#90EE90", "emoji": "🟢"},
}
