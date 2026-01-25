"""
US Markets fetcher - Dow, NASDAQ, S&P 500 and their futures.
Provides global risk sentiment for Indian market opening.
"""

import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch US market indices and futures."""
    results = {}

    # US Index futures (trade nearly 24 hours, good for pre-market sentiment)
    futures = {
        "es_futures": "ES=F",  # S&P 500 E-mini
        "nq_futures": "NQ=F",  # NASDAQ 100 E-mini
        "ym_futures": "YM=F",  # Dow E-mini
    }

    # Cash indices (for previous close reference)
    indices = {
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
    }

    # Fetch futures
    for key, ticker in futures.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                current = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                results[key] = round(float(current), 2)
                results[f"{key}_chg"] = round(float(change_pct), 2)
        except Exception as e:
            logger.warning(f"Failed to fetch {ticker}: {e}")

    # Fetch cash indices for reference
    for key, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                current = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                results[f"{key}_close"] = round(float(current), 2)
                results[f"{key}_chg"] = round(float(change_pct), 2)
        except Exception as e:
            logger.warning(f"Failed to fetch {ticker}: {e}")

    if not results:
        return None

    # Calculate overall US sentiment
    changes = []
    for key in ["sp500_chg", "nasdaq_chg", "dow_chg"]:
        if key in results:
            changes.append(results[key])

    if changes:
        avg_change = sum(changes) / len(changes)
        if avg_change > 0.5:
            sentiment = "Positive"
        elif avg_change < -0.5:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        results["us_sentiment"] = sentiment
        results["us_avg_chg"] = round(avg_change, 2)

    return results


def fetch_us_markets():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
