"""
Enhanced Bias Engine with additional market indicators.

Components:
1. FII Z-score (institutional flow momentum)
2. FII Cash Surprise (vs 20-day mean)
3. Futures OI Direction (FII long/short buildup)
4. PCR Level (options sentiment)
5. VIX Regime (volatility/fear)
6. Global Risk (S&P 500 large moves)
7. GIFT Nifty / Pre-market Gap (overnight sentiment)
8. US Markets Sentiment (Dow, NASDAQ, S&P)
9. NIFTY Trend (5-day momentum)
10. Fear & Greed Index (contrarian signal)
"""

from config.settings import (
    FII_ZSCORE_THRESHOLD,
    PCR_BULL_THRESHOLD,
    PCR_BEAR_THRESHOLD,
)


def compute_bias(features: dict, raw_data: dict) -> tuple[int, str, str]:
    """
    Compute institutional bias score from features.

    Args:
        features: dict from compute_features()
        raw_data: dict with all fetched indicator data

    Returns:
        (score, label, guidance) tuple

    Score range: approximately -8 to +8 with 10 components
    """
    score = 0
    components = {}  # Track individual contributions for debugging

    # === ORIGINAL COMPONENTS ===

    # Component 1: FII Z-score
    fii_z = features.get("fii_zscore", 0)
    if fii_z > FII_ZSCORE_THRESHOLD:
        score += 1
        components["fii_zscore"] = +1
    elif fii_z < -FII_ZSCORE_THRESHOLD:
        score -= 1
        components["fii_zscore"] = -1
    else:
        components["fii_zscore"] = 0

    # Component 2: FII Cash Surprise
    fii_surprise = features.get("fii_surprise", 0)
    if fii_surprise > 0:
        score += 1
        components["fii_surprise"] = +1
    elif fii_surprise < 0:
        score -= 1
        components["fii_surprise"] = -1
    else:
        components["fii_surprise"] = 0

    # Component 3: Futures OI Direction
    futures_dir = features.get("futures_direction", 0)
    score += futures_dir
    components["futures_oi"] = futures_dir

    # Component 4: PCR Level
    pcr = raw_data.get("pcr")
    if pcr is not None:
        if pcr > PCR_BULL_THRESHOLD:
            score += 1
            components["pcr"] = +1
        elif pcr < PCR_BEAR_THRESHOLD:
            score -= 1
            components["pcr"] = -1
        else:
            components["pcr"] = 0
    else:
        components["pcr"] = 0

    # Component 5: VIX Regime (high VIX = uncertainty = bearish pressure)
    if features.get("vix_flag", 0) == 1:
        score -= 1
        components["vix"] = -1
    else:
        components["vix"] = 0

    # Component 6: Global Risk (S&P 500)
    if features.get("global_risk_flag", 0) == 1:
        sp500_dir = features.get("sp500_direction", 0)
        score += sp500_dir
        components["sp500"] = sp500_dir
    else:
        components["sp500"] = 0

    # === NEW COMPONENTS ===

    # Component 7: GIFT Nifty / Pre-market Gap
    gift_sentiment = raw_data.get("gift_sentiment")
    if gift_sentiment == "Positive":
        score += 1
        components["gift_nifty"] = +1
    elif gift_sentiment == "Negative":
        score -= 1
        components["gift_nifty"] = -1
    else:
        components["gift_nifty"] = 0

    # Component 8: US Markets Sentiment
    us_sentiment = raw_data.get("us_sentiment")
    if us_sentiment == "Positive":
        score += 1
        components["us_markets"] = +1
    elif us_sentiment == "Negative":
        score -= 1
        components["us_markets"] = -1
    else:
        components["us_markets"] = 0

    # Component 9: NIFTY Trend (5-day momentum)
    nifty_trend_score = raw_data.get("nifty_trend_score", 0)
    # Trend score is already -2 to +2, scale to -1 to +1
    if nifty_trend_score >= 1:
        score += 1
        components["nifty_trend"] = +1
    elif nifty_trend_score <= -1:
        score -= 1
        components["nifty_trend"] = -1
    else:
        components["nifty_trend"] = 0

    # Component 10: Fear & Greed Index (CONTRARIAN signal)
    # Extreme greed = contrarian bearish, Extreme fear = contrarian bullish
    fear_greed_signal = raw_data.get("fear_greed_signal", 0)
    # Note: signal is already -1 (extreme fear = buy) or +1 (extreme greed = sell)
    # For bias, we SUBTRACT this (contrarian)
    if fear_greed_signal != 0:
        score -= fear_greed_signal  # Contrarian: extreme greed reduces score
        components["fear_greed"] = -fear_greed_signal
    else:
        components["fear_greed"] = 0

    # Map score to label and guidance
    label, guidance = _score_to_label(score)

    return score, label, guidance


def _score_to_label(score: int) -> tuple[str, str]:
    """
    Map integer score to bias label and trading guidance.

    With 10 components, score range is approximately -8 to +8.
    Adjusted thresholds accordingly.
    """
    if score >= 5:
        return (
            "Strong Bullish",
            "Multiple bullish signals aligned. Institutions and global cues favor upside. "
            "Consider buy-on-dips strategy."
        )
    elif score >= 2:
        return (
            "Bullish",
            "Net positive institutional flow with supportive global cues. "
            "Lean long with normal position sizing."
        )
    elif score >= -1:
        return (
            "Neutral",
            "Mixed signals across indicators. No clear directional edge. "
            "Reduce position sizes or wait for clarity."
        )
    elif score >= -4:
        return (
            "Bearish",
            "Net negative institutional flow. Global cues or trend not supportive. "
            "Lean short or stay flat."
        )
    else:
        return (
            "Strong Bearish",
            "Multiple bearish signals aligned. Institutions positioned short, global risk elevated. "
            "Avoid fresh longs, favor hedges or short positions."
        )


def get_component_breakdown(features: dict, raw_data: dict) -> dict:
    """
    Get detailed breakdown of each component's contribution.
    Useful for dashboard display.
    """
    breakdown = {
        "FII Z-score": {
            "value": features.get("fii_zscore", 0),
            "threshold": f">{FII_ZSCORE_THRESHOLD} bullish, <-{FII_ZSCORE_THRESHOLD} bearish",
        },
        "FII Surprise": {
            "value": features.get("fii_surprise", 0),
            "threshold": ">0 bullish, <0 bearish",
        },
        "Futures OI": {
            "value": features.get("futures_direction", 0),
            "threshold": "+1 long buildup, -1 short buildup",
        },
        "PCR": {
            "value": raw_data.get("pcr"),
            "threshold": f">{PCR_BULL_THRESHOLD} bullish, <{PCR_BEAR_THRESHOLD} bearish",
        },
        "VIX": {
            "value": raw_data.get("vix"),
            "threshold": ">15 = high vol (bearish pressure)",
        },
        "S&P 500": {
            "value": raw_data.get("sp500_change_pct"),
            "threshold": ">0.7% move triggers signal",
        },
        "GIFT Nifty": {
            "value": raw_data.get("gift_gap_pct"),
            "sentiment": raw_data.get("gift_sentiment"),
        },
        "US Markets": {
            "value": raw_data.get("us_avg_chg"),
            "sentiment": raw_data.get("us_sentiment"),
        },
        "NIFTY Trend": {
            "value": raw_data.get("nifty_5d_chg"),
            "trend": raw_data.get("nifty_trend"),
        },
        "Fear & Greed": {
            "value": raw_data.get("fear_greed_score"),
            "rating": raw_data.get("fear_greed_rating"),
            "note": "Contrarian signal",
        },
    }
    return breakdown
