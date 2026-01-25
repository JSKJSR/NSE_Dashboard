import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch S&P 500 previous day's change percentage."""
    ticker = yf.Ticker("^GSPC")
    hist = ticker.history(period="5d")
    if hist is None or len(hist) < 2:
        return None

    # Last two closes
    closes = hist["Close"].dropna()
    if len(closes) < 2:
        return None

    prev_close = closes.iloc[-1]
    prev_prev_close = closes.iloc[-2]
    change_pct = ((prev_close - prev_prev_close) / prev_prev_close) * 100

    # Get data date from index (the actual trading day)
    data_timestamp = hist.index[-1]
    data_date = data_timestamp.strftime("%Y-%m-%d") if hasattr(data_timestamp, 'strftime') else str(data_timestamp)[:10]

    return {
        "sp500_close": float(prev_close),
        "sp500_change_pct": round(float(change_pct), 2),
        "sp500_data_date": data_date,
    }


def fetch_sp500():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
