import logging
from nsepython import nse_optionchain_scrapper, pcr

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch NIFTY option chain and compute PCR (OI-based, near expiry)."""
    payload = nse_optionchain_scrapper("NIFTY")
    if not payload:
        return None

    # Try nsepython's pcr() first
    total_ce_oi = 0
    total_pe_oi = 0

    # Navigate the response structure — NSE may use 'records' or 'filtered'
    records = payload.get("records") or payload.get("filtered") or {}
    data = records.get("data", [])
    if not data:
        return None

    expiry_dates = records.get("expiryDates", [])
    near_expiry = expiry_dates[0] if expiry_dates else None

    for item in data:
        if near_expiry and item.get("expiryDate") != near_expiry:
            continue
        if "CE" in item:
            total_ce_oi += item["CE"].get("openInterest", 0)
        if "PE" in item:
            total_pe_oi += item["PE"].get("openInterest", 0)

    if total_ce_oi == 0:
        return None

    pcr_value = round(total_pe_oi / total_ce_oi, 4)

    return {
        "pcr": pcr_value,
        "total_ce_oi": total_ce_oi,
        "total_pe_oi": total_pe_oi,
    }


def fetch_option_chain_pcr():
    """Public interface with retry."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
