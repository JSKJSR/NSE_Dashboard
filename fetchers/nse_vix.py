import logging
from datetime import datetime
from nsepython import indiavix

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch India VIX current value."""
    vix = indiavix()
    if vix is None:
        return None
    # NSE VIX is real-time, use fetch time as data timestamp
    vix_data_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"vix": float(vix), "vix_data_ts": vix_data_ts}


def fetch_vix():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
