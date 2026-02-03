"""
GIFT Nifty fetcher.
Fetches live GIFT Nifty 50 Index Futures data from TradingView.

GIFT Nifty is traded on NSE International Exchange (NSE IX) in GIFT City.
Trading hours: 6:30 AM - 3:40 PM IST and 4:35 PM - 2:45 AM IST (21 hours/day)
"""

import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

TRADINGVIEW_API = "https://scanner.tradingview.com/symbol"
GIFT_NIFTY_SYMBOL = "NSEIX:NIFTY1!"
NIFTY_50_SYMBOL = "NSE:NIFTY"


def _fetch():
    """
    Fetch live GIFT Nifty data from TradingView.

    Returns:
        dict with gift_nifty, gift_gap_pct, gift_sentiment, etc.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    # Fetch GIFT Nifty futures price
    params = {
        'symbol': GIFT_NIFTY_SYMBOL,
        'fields': 'close,open,high,low,change,change_abs,volume,description',
        'no_404': 'true'
    }

    try:
        resp = requests.get(TRADINGVIEW_API, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        gift_data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch GIFT Nifty: {e}")
        return None

    gift_price = gift_data.get('close')
    if not gift_price:
        logger.error("No GIFT Nifty price data received")
        return None

    # Fetch NIFTY 50 spot price for gap calculation
    params['symbol'] = NIFTY_50_SYMBOL
    try:
        resp = requests.get(TRADINGVIEW_API, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        nifty_data = resp.json()
        nifty_close = nifty_data.get('close', gift_price)
    except Exception:
        # If we can't get NIFTY spot, use GIFT Nifty's own change
        nifty_close = gift_price

    # Calculate gap percentage (GIFT Nifty vs NIFTY 50 spot)
    if nifty_close and nifty_close > 0:
        gap_pct = ((gift_price - nifty_close) / nifty_close) * 100
    else:
        gap_pct = gift_data.get('change', 0)

    # Determine sentiment based on gap
    if gap_pct > 0.3:
        sentiment = "Positive"
    elif gap_pct < -0.3:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    # Data date is today since this is live futures data
    data_date = datetime.now().strftime("%Y-%m-%d")

    return {
        "gift_nifty": round(gift_price, 2),
        "nifty_prev_close": round(nifty_close, 2),
        "gift_gap_pct": round(gap_pct, 2),
        "gift_sentiment": sentiment,
        "gift_change_pct": round(gift_data.get('change', 0), 2),
        "gift_open": gift_data.get('open'),
        "gift_high": gift_data.get('high'),
        "gift_low": gift_data.get('low'),
        "gift_volume": gift_data.get('volume'),
        "gift_data_date": data_date,
    }


def fetch_gift_nifty():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
