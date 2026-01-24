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
        raw_data: dict with pcr, sp500_change_pct, etc.

    Returns:
        (score, label, guidance) tuple
    """
    score = 0

    # Component 1: FII Z-score
    fii_z = features.get("fii_zscore", 0)
    if fii_z > FII_ZSCORE_THRESHOLD:
        score += 1
    elif fii_z < -FII_ZSCORE_THRESHOLD:
        score -= 1

    # Component 2: FII Cash Surprise
    fii_surprise = features.get("fii_surprise", 0)
    if fii_surprise > 0:
        score += 1
    elif fii_surprise < 0:
        score -= 1

    # Component 3: Futures OI Direction
    futures_dir = features.get("futures_direction", 0)
    score += futures_dir

    # Component 4: PCR Level
    pcr = raw_data.get("pcr")
    if pcr is not None:
        if pcr > PCR_BULL_THRESHOLD:
            score += 1
        elif pcr < PCR_BEAR_THRESHOLD:
            score -= 1

    # Component 5: VIX Regime (high VIX = uncertainty = bearish pressure)
    if features.get("vix_flag", 0) == 1:
        score -= 1

    # Component 6: Global Risk
    if features.get("global_risk_flag", 0) == 1:
        sp500_dir = features.get("sp500_direction", 0)
        score += sp500_dir

    # Map score to label and guidance
    label, guidance = _score_to_label(score)

    return score, label, guidance


def _score_to_label(score: int) -> tuple[str, str]:
    """Map integer score to bias label and trading guidance."""
    if score >= 4:
        return (
            "Strong Bullish",
            "Institutions strongly positioned long. Favor buy-on-dips."
        )
    elif score >= 2:
        return (
            "Bullish",
            "Net positive institutional flow. Lean long with normal risk."
        )
    elif score >= -1:
        return (
            "Neutral",
            "Mixed institutional signals. No clear directional edge today."
        )
    elif score >= -3:
        return (
            "Bearish",
            "Net negative institutional flow. Lean short or stay flat."
        )
    else:
        return (
            "Strong Bearish",
            "Institutions positioned short. Avoid fresh longs, favor hedges."
        )
