import logging
from nsepython import indiavix

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch India VIX current value."""
    vix = indiavix()
    if vix is None:
        return None
    return {"vix": float(vix)}


def fetch_vix():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
