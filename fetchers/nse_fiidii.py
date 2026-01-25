import logging
from datetime import datetime
from nsepython import nse_fiidii

logger = logging.getLogger(__name__)


def _fetch():
    """Fetch FII/DII cash market data from NSE."""
    df = nse_fiidii(mode="pandas")
    if df is None or df.empty:
        return None

    # Filter for Cash Market category
    cash = df[df["category"].str.contains("Cash", case=False, na=False)]
    if cash.empty:
        # Fallback: use first available rows
        cash = df

    result = {}
    nse_date = None

    for _, row in cash.iterrows():
        cat = row.get("category", "")
        # Extract date from NSE response (format: "23-Jan-2026")
        if nse_date is None and "date" in row:
            try:
                date_str = row["date"]
                parsed = datetime.strptime(date_str, "%d-%b-%Y")
                nse_date = parsed.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        if "FII" in cat or "FPI" in cat:
            result["fii_buy"] = float(row.get("buyValue", 0))
            result["fii_sell"] = float(row.get("sellValue", 0))
            result["fii_net"] = float(row.get("netValue", 0))
        elif "DII" in cat:
            result["dii_buy"] = float(row.get("buyValue", 0))
            result["dii_sell"] = float(row.get("sellValue", 0))
            result["dii_net"] = float(row.get("netValue", 0))

    if "fii_net" not in result:
        return None

    # Include the actual data date from NSE
    if nse_date:
        result["nse_data_date"] = nse_date

    return result


def fetch_fiidii():
    """Public interface with logging."""
    from fetchers.retry import fetch_with_retry
    return fetch_with_retry(_fetch)
