import numpy as np
import pandas as pd

from config.settings import (
    ROLLING_WINDOW,
    VIX_HIGH_THRESHOLD,
    SP500_MOVE_THRESHOLD,
)


def compute_features(today_data: dict, history_df: pd.DataFrame) -> dict:
    """
    Compute derived features from today's raw data and historical rows.

    Args:
        today_data: dict with keys fii_net, dii_net, fii_net_oi, pcr, vix, sp500_change_pct
        history_df: DataFrame of previous daily_data rows (ascending by date)

    Returns:
        dict of computed features
    """
    features = {}

    # --- FII Z-score (20-day rolling) ---
    fii_net_today = today_data.get("fii_net", 0) or 0
    if not history_df.empty and "fii_net" in history_df.columns:
        fii_series = history_df["fii_net"].dropna().tail(ROLLING_WINDOW)
        if len(fii_series) >= 2:
            mean = fii_series.mean()
            std = fii_series.std(ddof=1)
            features["fii_zscore"] = round((fii_net_today - mean) / std, 3) if std > 0 else 0.0
            features["fii_surprise"] = round(fii_net_today - mean, 2)
        else:
            features["fii_zscore"] = 0.0
            features["fii_surprise"] = 0.0
    else:
        features["fii_zscore"] = 0.0
        features["fii_surprise"] = 0.0

    # --- DII Surprise ---
    dii_net_today = today_data.get("dii_net", 0) or 0
    if not history_df.empty and "dii_net" in history_df.columns:
        dii_series = history_df["dii_net"].dropna().tail(ROLLING_WINDOW)
        if len(dii_series) >= 2:
            mean = dii_series.mean()
            features["dii_surprise"] = round(dii_net_today - mean, 2)
        else:
            features["dii_surprise"] = 0.0
    else:
        features["dii_surprise"] = 0.0

    # --- Futures OI Direction ---
    fii_net_oi_today = today_data.get("fii_net_oi")
    if fii_net_oi_today is not None and not history_df.empty and "fii_net_oi" in history_df.columns:
        prev_oi = history_df["fii_net_oi"].dropna()
        if len(prev_oi) > 0:
            yesterday_net_oi = prev_oi.iloc[-1]
            change = fii_net_oi_today - yesterday_net_oi
            features["futures_direction"] = int(np.sign(change))
        else:
            features["futures_direction"] = 0
    else:
        features["futures_direction"] = 0

    # --- PCR Change (day-over-day) ---
    pcr_today = today_data.get("pcr")
    if pcr_today is not None and not history_df.empty and "pcr" in history_df.columns:
        prev_pcr = history_df["pcr"].dropna()
        if len(prev_pcr) > 0:
            features["pcr_change"] = round(pcr_today - prev_pcr.iloc[-1], 4)
        else:
            features["pcr_change"] = 0.0
    else:
        features["pcr_change"] = 0.0

    # --- VIX Regime Flag ---
    vix = today_data.get("vix")
    features["vix_flag"] = 1 if (vix is not None and vix > VIX_HIGH_THRESHOLD) else 0

    # --- Global Risk Flag ---
    sp500_chg = today_data.get("sp500_change_pct", 0) or 0
    features["global_risk_flag"] = 1 if abs(sp500_chg) > SP500_MOVE_THRESHOLD else 0
    features["sp500_direction"] = int(np.sign(sp500_chg)) if sp500_chg != 0 else 0

    return features
