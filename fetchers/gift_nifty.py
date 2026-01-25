"""
GIFT Nifty (formerly SGX Nifty) fetcher.
Provides pre-market indication of NIFTY 50 opening.

Since GIFT Nifty doesn't have a free API, we estimate the expected gap
using global futures (S&P 500, Dow, NASDAQ) which are highly correlated
with NIFTY opening gaps.
"""

import logging
import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)


def _fetch():
    """
    Estimate GIFT Nifty / expected NIFTY gap using global indices.

    Research shows NIFTY opening gaps are correlated with:
    - S&P 500 overnight change (~0.4-0.6 correlation)
    - US market close vs previous close
    """
    # Get NIFTY 50 last close
    nifty = yf.Ticker("^NSEI")
    nifty_hist = nifty.history(period="5d")
    if nifty_hist.empty:
        return None

    nifty_close = float(nifty_hist["Close"].iloc[-1])

    # Get data timestamp
    nifty_ts = nifty_hist.index[-1]
    gift_data_ts = nifty_ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(nifty_ts, 'strftime') else str(nifty_ts)

    # Get US market changes (cash indices are more reliable than futures on weekends)
    us_changes = []

    indices = [
        ("^GSPC", "S&P 500"),
        ("^IXIC", "NASDAQ"),
        ("^DJI", "Dow"),
    ]

    for ticker, name in indices:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                change = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100
                us_changes.append(change)
        except Exception:
            pass

    if not us_changes:
        # Return neutral if no US data available
        return {
            "gift_nifty": round(nifty_close, 2),
            "nifty_prev_close": round(nifty_close, 2),
            "gift_gap_pct": 0.0,
            "gift_sentiment": "Neutral",
            "global_avg_chg": 0.0,
            "gift_data_ts": gift_data_ts,
        }

    # Average US market change
    avg_us_change = np.mean(us_changes)

    # NIFTY typically moves ~0.5-0.7x of US overnight move
    # Using 0.6 as the correlation factor
    estimated_gap_pct = avg_us_change * 0.6

    # Estimate GIFT Nifty price
    gift_price = nifty_close * (1 + estimated_gap_pct / 100)

    # Determine sentiment
    if estimated_gap_pct > 0.5:
        sentiment = "Positive"
    elif estimated_gap_pct < -0.5:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return {
        "gift_nifty": round(gift_price, 2),
        "nifty_prev_close": round(nifty_close, 2),
        "gift_gap_pct": round(estimated_gap_pct, 2),
        "gift_sentiment": sentiment,
        "global_avg_chg": round(avg_us_change, 2),
        "gift_data_ts": gift_data_ts,
    }


def fetch_gift_nifty():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
