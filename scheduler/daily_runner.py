#!/usr/bin/env python3
"""
Daily runner: Fetches NSE data, computes features and bias, stores in SQLite.
Intended to run at 16:15 IST on trading days via macOS launchd.

Usage:
    python scheduler/daily_runner.py              # Run for today
    python scheduler/daily_runner.py --backfill 30  # Seed last 30 days (S&P only, NSE live only)
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LOG_DIR
from storage.database import init_db
from storage.queries import insert_daily_row, insert_fetch_log, get_last_n_rows, date_exists
from fetchers.nse_fiidii import fetch_fiidii
from fetchers.nse_futures_oi import fetch_futures_oi
from fetchers.nse_option_chain import fetch_option_chain_pcr
from fetchers.nse_vix import fetch_vix
from fetchers.sp500 import fetch_sp500
from core.features import compute_features
from core.bias_engine import compute_bias


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "daily_runner.log"),
            logging.StreamHandler(),
        ],
    )


def is_weekday(date: datetime) -> bool:
    return date.weekday() < 5  # Mon=0, Fri=4


def run_daily(target_date: datetime = None):
    """Main pipeline: fetch -> compute -> store."""
    logger = logging.getLogger("daily_runner")

    if target_date is None:
        target_date = datetime.now()

    date_str = target_date.strftime("%Y-%m-%d")

    if not is_weekday(target_date):
        logger.info(f"{date_str} is a weekend. Skipping.")
        return

    if date_exists(date_str):
        logger.info(f"{date_str} already processed. Skipping.")
        return

    logger.info(f"=== Processing {date_str} ===")

    # --- Fetch all sources ---
    data_complete = 1
    raw = {"date": date_str}

    # 1. FII/DII
    fiidii = fetch_fiidii()
    if fiidii:
        raw.update(fiidii)
        insert_fetch_log(date_str, "fiidii", "success")
        logger.info(f"FII/DII: FII net={fiidii.get('fii_net')}, DII net={fiidii.get('dii_net')}")
    else:
        data_complete = 0
        insert_fetch_log(date_str, "fiidii", "failed", error_message="All retries exhausted")
        logger.warning("FII/DII fetch failed")

    # 2. Futures OI
    oi_date_str = target_date.strftime("%d%m%Y")
    futures = fetch_futures_oi(oi_date_str)
    if futures:
        raw.update(futures)
        insert_fetch_log(date_str, "futures_oi", "success")
        logger.info(f"Futures OI: net={futures.get('fii_net_oi')}")
    else:
        data_complete = 0
        insert_fetch_log(date_str, "futures_oi", "failed", error_message="All retries exhausted")
        logger.warning("Futures OI fetch failed")

    # 3. Option Chain PCR
    pcr_data = fetch_option_chain_pcr()
    if pcr_data:
        raw.update(pcr_data)
        insert_fetch_log(date_str, "option_chain", "success")
        logger.info(f"PCR: {pcr_data.get('pcr')}")
    else:
        data_complete = 0
        insert_fetch_log(date_str, "option_chain", "failed", error_message="All retries exhausted")
        logger.warning("Option chain PCR fetch failed")

    # 4. VIX
    vix_data = fetch_vix()
    if vix_data:
        raw.update(vix_data)
        insert_fetch_log(date_str, "vix", "success")
        logger.info(f"VIX: {vix_data.get('vix')}")
    else:
        data_complete = 0
        insert_fetch_log(date_str, "vix", "failed", error_message="All retries exhausted")
        logger.warning("VIX fetch failed")

    # 5. S&P 500
    sp500 = fetch_sp500()
    if sp500:
        raw.update(sp500)
        insert_fetch_log(date_str, "sp500", "success")
        logger.info(f"S&P 500: {sp500.get('sp500_change_pct')}%")
    else:
        # Non-critical: default to neutral
        raw["sp500_close"] = None
        raw["sp500_change_pct"] = 0.0
        insert_fetch_log(date_str, "sp500", "failed", error_message="Defaulting to neutral")
        logger.warning("S&P 500 fetch failed, defaulting to neutral")

    # --- Compute features ---
    history = get_last_n_rows(20)
    features = compute_features(raw, history)
    logger.info(f"Features: {features}")

    # --- Compute bias ---
    score, label, guidance = compute_bias(features, raw)
    logger.info(f"Bias: score={score}, label={label}")

    # --- Store ---
    row = {
        "date": date_str,
        "fii_buy": raw.get("fii_buy"),
        "fii_sell": raw.get("fii_sell"),
        "fii_net": raw.get("fii_net"),
        "dii_buy": raw.get("dii_buy"),
        "dii_sell": raw.get("dii_sell"),
        "dii_net": raw.get("dii_net"),
        "fii_long_oi": raw.get("fii_long_oi"),
        "fii_short_oi": raw.get("fii_short_oi"),
        "fii_net_oi": raw.get("fii_net_oi"),
        "pcr": raw.get("pcr"),
        "total_ce_oi": raw.get("total_ce_oi"),
        "total_pe_oi": raw.get("total_pe_oi"),
        "vix": raw.get("vix"),
        "sp500_close": raw.get("sp500_close"),
        "sp500_change_pct": raw.get("sp500_change_pct"),
        "fii_zscore": features.get("fii_zscore"),
        "fii_surprise": features.get("fii_surprise"),
        "dii_surprise": features.get("dii_surprise"),
        "futures_direction": features.get("futures_direction"),
        "pcr_change": features.get("pcr_change"),
        "vix_flag": features.get("vix_flag"),
        "global_risk_flag": features.get("global_risk_flag"),
        "sp500_direction": features.get("sp500_direction"),
        "bias_score": score,
        "bias_label": label,
        "bias_guidance": guidance,
        "fetch_timestamp": datetime.now().isoformat(),
        "data_complete": data_complete,
    }

    insert_daily_row(row)
    logger.info(f"Stored: {date_str} | Score={score} | {label}")
    return row


def main():
    parser = argparse.ArgumentParser(description="NSE Bias Dashboard Daily Runner")
    parser.add_argument("--backfill", type=int, default=0,
                        help="Number of past days to attempt backfill (live fetch, today only)")
    args = parser.parse_args()

    setup_logging()
    init_db()

    if args.backfill > 0:
        logger = logging.getLogger("daily_runner")
        logger.info(f"Backfill mode: running for today (NSE provides live data only)")
        run_daily()
    else:
        run_daily()


if __name__ == "__main__":
    main()
