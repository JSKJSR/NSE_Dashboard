import logging
import ssl
import os
from datetime import datetime, timedelta

# Fix macOS SSL cert issue for urllib (used by nsepython internally)
if not os.environ.get("SSL_CERT_FILE"):
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()

from nsepython import get_fao_participant_oi

logger = logging.getLogger(__name__)


def _fetch(date_str: str = None):
    """
    Fetch FII index futures participant OI.
    date_str: 'DDMMYYYY' format. Defaults to today.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%d%m%Y")

    df = get_fao_participant_oi(date_str)
    if df is None or (hasattr(df, 'empty') and df.empty):
        return None

    # The CSV has columns: Client Type, Future Index Long, Future Index Short, etc.
    # Look for FII/FPI row
    fii_row = None
    if hasattr(df, 'iterrows'):
        for _, row in df.iterrows():
            client = str(row.iloc[0]).upper() if len(row) > 0 else ""
            if "FII" in client or "FPI" in client:
                fii_row = row
                break

    if fii_row is None:
        return None

    # Columns typically: Client Type, Future Index Long, Future Index Short,
    # Future Stock Long, Future Stock Short, Option Index Call Long, ...
    try:
        fii_long = int(str(fii_row.iloc[1]).replace(",", "").strip())
        fii_short = int(str(fii_row.iloc[2]).replace(",", "").strip())
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse futures OI: {e}")
        return None

    return {
        "fii_long_oi": fii_long,
        "fii_short_oi": fii_short,
        "fii_net_oi": fii_long - fii_short,
    }


def fetch_futures_oi(date_str: str = None):
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch, date_str)
