"""
NIFTY 50 trend analysis fetcher.
Provides 5-day trend, support/resistance levels, and momentum indicators.
"""

import logging
import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch NIFTY 50 price data and compute trend indicators."""
    ticker = yf.Ticker("^NSEI")

    # Get 30 days of data for trend analysis
    hist = ticker.history(period="30d")
    if hist.empty or len(hist) < 5:
        return None

    closes = hist["Close"].values
    highs = hist["High"].values
    lows = hist["Low"].values

    # Get data date from index (the actual trading day)
    data_timestamp = hist.index[-1]
    nifty_data_date = data_timestamp.strftime("%Y-%m-%d") if hasattr(data_timestamp, 'strftime') else str(data_timestamp)[:10]

    # Current price
    current_price = float(closes[-1])

    # 5-day change
    if len(closes) >= 5:
        five_day_ago = float(closes[-5])
        five_day_chg = ((current_price - five_day_ago) / five_day_ago) * 100
    else:
        five_day_chg = 0.0

    # 20-day change (monthly trend)
    if len(closes) >= 20:
        twenty_day_ago = float(closes[-20])
        twenty_day_chg = ((current_price - twenty_day_ago) / twenty_day_ago) * 100
    else:
        twenty_day_chg = five_day_chg

    # Simple moving averages
    sma_5 = float(np.mean(closes[-5:])) if len(closes) >= 5 else current_price
    sma_20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else current_price

    # Trend direction based on price vs SMAs
    above_sma5 = current_price > sma_5
    above_sma20 = current_price > sma_20

    # RSI calculation (14-period)
    if len(closes) >= 15:
        deltas = np.diff(closes[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50.0  # Neutral default

    # Support and resistance (simple pivot-based)
    recent_high = float(np.max(highs[-5:]))
    recent_low = float(np.min(lows[-5:]))
    pivot = (recent_high + recent_low + current_price) / 3
    resistance_1 = 2 * pivot - recent_low
    support_1 = 2 * pivot - recent_high

    # Determine overall trend
    if five_day_chg > 1.5 and above_sma5 and above_sma20:
        trend = "Strong Uptrend"
        trend_score = 2
    elif five_day_chg > 0.5 and above_sma5:
        trend = "Uptrend"
        trend_score = 1
    elif five_day_chg < -1.5 and not above_sma5 and not above_sma20:
        trend = "Strong Downtrend"
        trend_score = -2
    elif five_day_chg < -0.5 and not above_sma5:
        trend = "Downtrend"
        trend_score = -1
    else:
        trend = "Sideways"
        trend_score = 0

    return {
        "nifty_price": round(current_price, 2),
        "nifty_5d_chg": round(five_day_chg, 2),
        "nifty_20d_chg": round(twenty_day_chg, 2),
        "nifty_sma5": round(sma_5, 2),
        "nifty_sma20": round(sma_20, 2),
        "nifty_rsi": round(rsi, 2),
        "nifty_trend": trend,
        "nifty_trend_score": trend_score,
        "nifty_support": round(support_1, 2),
        "nifty_resistance": round(resistance_1, 2),
        "nifty_data_date": nifty_data_date,
    }


def fetch_nifty_trend():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
