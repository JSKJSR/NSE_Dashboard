"""
CNN Fear & Greed Index fetcher.
Provides overall market sentiment based on 7 indicators.
"""

import logging
import requests

logger = logging.getLogger(__name__)

FEAR_GREED_API = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"


def _fetch():
    """Fetch CNN Fear & Greed Index."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(FEAR_GREED_API, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Fear & Greed API returned {resp.status_code}")
            return None

        data = resp.json()

        # Extract current reading
        fear_greed_data = data.get("fear_and_greed", {})
        current_score = fear_greed_data.get("score")
        current_rating = fear_greed_data.get("rating")
        previous_close = fear_greed_data.get("previous_close")
        previous_1_week = fear_greed_data.get("previous_1_week")
        previous_1_month = fear_greed_data.get("previous_1_month")
        previous_1_year = fear_greed_data.get("previous_1_year")

        if current_score is None:
            return None

        # Determine sentiment category
        score = float(current_score)
        if score >= 75:
            sentiment = "Extreme Greed"
            signal = 1  # Contrarian bearish (market overheated)
        elif score >= 55:
            sentiment = "Greed"
            signal = 0
        elif score >= 45:
            sentiment = "Neutral"
            signal = 0
        elif score >= 25:
            sentiment = "Fear"
            signal = 0
        else:
            sentiment = "Extreme Fear"
            signal = -1  # Contrarian bullish (market oversold)

        return {
            "fear_greed_score": round(score, 1),
            "fear_greed_rating": current_rating or sentiment,
            "fear_greed_prev_close": float(previous_close) if previous_close else None,
            "fear_greed_1w_ago": float(previous_1_week) if previous_1_week else None,
            "fear_greed_1m_ago": float(previous_1_month) if previous_1_month else None,
            "fear_greed_signal": signal,  # -1 = contrarian buy, +1 = contrarian sell
        }

    except Exception as e:
        logger.warning(f"Failed to fetch Fear & Greed Index: {e}")
        return None


def fetch_fear_greed():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
