#!/usr/bin/env python3
"""
NIFTY Daily Institutional Bias Dashboard — Streamlit App.

Enhanced with global market indicators:
- GIFT Nifty (pre-market gap)
- US Markets (Dow, NASDAQ, S&P)
- NIFTY Trend (5-day momentum)
- Fear & Greed Index

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from storage.database import init_db
from storage.queries import get_latest_row, get_last_n_days, date_exists

# --- Page Config ---
st.set_page_config(
    page_title="NIFTY Bias Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize DB (creates tables if needed)
init_db()


# --- Data Fetch Function ---
def fetch_and_store_data():
    """Run the daily data fetch pipeline with all indicators."""
    from fetchers.nse_fiidii import fetch_fiidii
    from fetchers.nse_futures_oi import fetch_futures_oi
    from fetchers.nse_option_chain import fetch_option_chain_pcr
    from fetchers.nse_vix import fetch_vix
    from fetchers.sp500 import fetch_sp500
    from fetchers.gift_nifty import fetch_gift_nifty
    from fetchers.us_markets import fetch_us_markets
    from fetchers.nifty_trend import fetch_nifty_trend
    from fetchers.fear_greed import fetch_fear_greed
    from core.features import compute_features
    from core.bias_engine import compute_bias
    from storage.queries import insert_daily_row, get_last_n_rows

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    data_complete = 1
    raw = {"date": date_str}
    status_messages = []

    # === CORE NSE DATA ===

    with st.spinner("Fetching FII/DII data..."):
        fiidii = fetch_fiidii()
        if fiidii:
            raw.update(fiidii)
            nse_date = fiidii.get("nse_data_date")
            if nse_date:
                raw["date"] = nse_date
                date_str = nse_date
            status_messages.append(f"FII/DII: FII={fiidii.get('fii_net'):,.0f} Cr")
        else:
            data_complete = 0
            status_messages.append("FII/DII: Failed")

    with st.spinner("Fetching Futures OI..."):
        oi_date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d%m%Y")
        futures = fetch_futures_oi(oi_date_str)
        if futures:
            raw.update(futures)
            status_messages.append(f"Futures OI: {futures.get('fii_net_oi'):,}")
        else:
            data_complete = 0
            status_messages.append("Futures OI: Failed")

    with st.spinner("Fetching Option Chain PCR..."):
        pcr_data = fetch_option_chain_pcr()
        if pcr_data:
            raw.update(pcr_data)
            status_messages.append(f"PCR: {pcr_data.get('pcr'):.3f}")
        else:
            status_messages.append("PCR: N/A (market closed)")

    with st.spinner("Fetching VIX..."):
        vix_data = fetch_vix()
        if vix_data:
            raw.update(vix_data)
            status_messages.append(f"VIX: {vix_data.get('vix'):.2f}")
        else:
            data_complete = 0
            status_messages.append("VIX: Failed")

    with st.spinner("Fetching S&P 500..."):
        sp500 = fetch_sp500()
        if sp500:
            raw.update(sp500)
            status_messages.append(f"S&P 500: {sp500.get('sp500_change_pct'):+.2f}%")
        else:
            raw["sp500_close"] = None
            raw["sp500_change_pct"] = 0.0
            status_messages.append("S&P 500: N/A")

    # === NEW GLOBAL INDICATORS ===

    with st.spinner("Fetching GIFT Nifty..."):
        gift = fetch_gift_nifty()
        if gift:
            raw.update(gift)
            status_messages.append(f"GIFT Nifty: {gift.get('gift_sentiment')}")
        else:
            status_messages.append("GIFT Nifty: N/A")

    with st.spinner("Fetching US Markets..."):
        us_markets = fetch_us_markets()
        if us_markets:
            raw.update(us_markets)
            status_messages.append(f"US Markets: {us_markets.get('us_sentiment')}")
        else:
            status_messages.append("US Markets: N/A")

    with st.spinner("Fetching NIFTY Trend..."):
        nifty_trend = fetch_nifty_trend()
        if nifty_trend:
            raw.update(nifty_trend)
            status_messages.append(f"NIFTY: {nifty_trend.get('nifty_trend')}")
        else:
            status_messages.append("NIFTY Trend: N/A")

    with st.spinner("Fetching Fear & Greed..."):
        fear_greed = fetch_fear_greed()
        if fear_greed:
            raw.update(fear_greed)
            status_messages.append(f"Fear & Greed: {fear_greed.get('fear_greed_score'):.0f}")
        else:
            status_messages.append("Fear & Greed: N/A")

    # === COMPUTE FEATURES AND BIAS ===

    with st.spinner("Computing bias..."):
        history = get_last_n_rows(20)
        features = compute_features(raw, history)
        score, label, guidance = compute_bias(features, raw)

    # === STORE ===

    row = {
        "date": date_str,
        # FII/DII
        "fii_buy": raw.get("fii_buy"),
        "fii_sell": raw.get("fii_sell"),
        "fii_net": raw.get("fii_net"),
        "dii_buy": raw.get("dii_buy"),
        "dii_sell": raw.get("dii_sell"),
        "dii_net": raw.get("dii_net"),
        # Futures OI
        "fii_long_oi": raw.get("fii_long_oi"),
        "fii_short_oi": raw.get("fii_short_oi"),
        "fii_net_oi": raw.get("fii_net_oi"),
        # Options/PCR
        "pcr": raw.get("pcr"),
        "total_ce_oi": raw.get("total_ce_oi"),
        "total_pe_oi": raw.get("total_pe_oi"),
        # VIX
        "vix": raw.get("vix"),
        # S&P 500
        "sp500_close": raw.get("sp500_close"),
        "sp500_change_pct": raw.get("sp500_change_pct"),
        # GIFT Nifty
        "gift_nifty": raw.get("gift_nifty"),
        "gift_gap_pct": raw.get("gift_gap_pct"),
        "gift_sentiment": raw.get("gift_sentiment"),
        # US Markets
        "us_sentiment": raw.get("us_sentiment"),
        "us_avg_chg": raw.get("us_avg_chg"),
        "dow_chg": raw.get("dow_chg"),
        "nasdaq_chg": raw.get("nasdaq_chg"),
        # NIFTY Trend
        "nifty_price": raw.get("nifty_price"),
        "nifty_5d_chg": raw.get("nifty_5d_chg"),
        "nifty_20d_chg": raw.get("nifty_20d_chg"),
        "nifty_rsi": raw.get("nifty_rsi"),
        "nifty_trend": raw.get("nifty_trend"),
        "nifty_trend_score": raw.get("nifty_trend_score"),
        # Fear & Greed
        "fear_greed_score": raw.get("fear_greed_score"),
        "fear_greed_rating": raw.get("fear_greed_rating"),
        "fear_greed_signal": raw.get("fear_greed_signal"),
        # Data source dates (actual trading day of the data)
        "sp500_data_date": raw.get("sp500_data_date"),
        "us_data_date": raw.get("us_data_date"),
        "nifty_data_date": raw.get("nifty_data_date"),
        "gift_data_date": raw.get("gift_data_date"),
        "fg_data_date": raw.get("fg_data_date"),
        "vix_data_date": raw.get("vix_data_date"),
        # Computed features
        "fii_zscore": features.get("fii_zscore"),
        "fii_surprise": features.get("fii_surprise"),
        "dii_surprise": features.get("dii_surprise"),
        "futures_direction": features.get("futures_direction"),
        "pcr_change": features.get("pcr_change"),
        "vix_flag": features.get("vix_flag"),
        "global_risk_flag": features.get("global_risk_flag"),
        "sp500_direction": features.get("sp500_direction"),
        # Bias result
        "bias_score": score,
        "bias_label": label,
        "bias_guidance": guidance,
        # Metadata
        "fetch_timestamp": datetime.now().isoformat(),
        "data_complete": data_complete,
    }
    insert_daily_row(row)

    return score, label, status_messages, data_complete


# --- Sidebar ---
st.sidebar.title("Settings")
refresh_seconds = st.sidebar.selectbox(
    "Auto-refresh interval",
    options=[0, 30, 60, 300],
    format_func=lambda x: "Off" if x == 0 else f"{x}s",
    index=0,
)
chart_days = st.sidebar.slider("Chart history (days)", 7, 90, 30)

st.sidebar.markdown("---")
st.sidebar.subheader("Data Refresh")

today_str = datetime.now().strftime("%Y-%m-%d")
has_today = date_exists(today_str)

latest_for_sidebar = get_latest_row()
if latest_for_sidebar:
    latest_date = latest_for_sidebar.get('date', 'N/A')
    if has_today:
        st.sidebar.success(f"Today's data loaded ({today_str})")
    else:
        st.sidebar.info(f"Showing: {latest_date}")
        st.sidebar.caption("(Today's data not yet available)")
else:
    st.sidebar.warning("No data available")

if st.sidebar.button("Fetch Now", type="primary", use_container_width=True):
    try:
        score, label, messages, complete = fetch_and_store_data()
        st.sidebar.success(f"Fetched! Bias: {score:+d} ({label})")
        for msg in messages:
            st.sidebar.caption(msg)
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Fetch failed: {e}")

if refresh_seconds > 0:
    st.rerun()


# --- Helper Functions ---
def bias_color(label: str) -> str:
    colors = {
        "Strong Bullish": "#00C853",
        "Bullish": "#66BB6A",
        "Neutral": "#9E9E9E",
        "Bearish": "#FF7043",
        "Strong Bearish": "#D32F2F",
    }
    return colors.get(label, "#9E9E9E")


def sentiment_color(sentiment: str) -> str:
    if sentiment == "Positive":
        return "#00C853"
    elif sentiment == "Negative":
        return "#D32F2F"
    return "#9E9E9E"


def signal_arrow(value, bull_thresh, bear_thresh) -> str:
    if value is None:
        return "-"
    if value > bull_thresh:
        return "+1"
    elif value < bear_thresh:
        return "-1"
    return "0"


# --- Main Content ---
st.title("NIFTY Daily Institutional Bias Dashboard")

latest = get_latest_row()

if latest is None:
    st.warning("No data available yet.")
    st.info("Click **Fetch Now** in the sidebar to load today's data.")

    if st.button("Fetch Data Now", type="primary"):
        try:
            score, label, messages, complete = fetch_and_store_data()
            st.success(f"Data fetched! Bias: {score:+d} ({label})")
            for msg in messages:
                st.caption(msg)
            st.rerun()
        except Exception as e:
            st.error(f"Fetch failed: {e}")
    st.stop()

# --- Current Bias Display ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    score = latest.get("bias_score", 0) or 0
    label = latest.get("bias_label", "Unknown")
    color = bias_color(label)

    st.markdown(
        f"""
        <div style="text-align:center; padding:20px;">
            <h1 style="color:{color}; font-size:64px; margin:0;">{score:+d}</h1>
            <h3 style="color:{color}; margin:5px 0;">{label}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(f"**Guidance:** {latest.get('bias_guidance', 'N/A')}")
    data_date = latest.get('date', 'N/A')
    try:
        data_date_obj = datetime.strptime(data_date, "%Y-%m-%d")
        data_date_formatted = data_date_obj.strftime("%A, %d %b %Y")
    except:
        data_date_formatted = data_date
    st.markdown(f"**Data Date:** {data_date_formatted}")
    fetch_ts_raw = latest.get('fetch_timestamp', '')
    if fetch_ts_raw:
        try:
            fetch_dt_main = datetime.fromisoformat(fetch_ts_raw)
            fetch_formatted = fetch_dt_main.strftime("%d %b %Y, %I:%M:%S %p")
        except:
            fetch_formatted = fetch_ts_raw[:19]
        st.markdown(f"**Fetched:** {fetch_formatted}")
    if data_date != today_str:
        st.info(f"Showing last available data (market may be closed)")
    if latest.get("data_complete") == 0:
        st.warning("Some data sources failed. Bias may be less reliable.")

with col3:
    st.markdown("**Score Breakdown (10 Components)**")
    breakdown_data = [
        {"Component": "FII Z-score", "Value": f"{latest.get('fii_zscore', 0) or 0:.2f}", "Signal": signal_arrow(latest.get("fii_zscore"), 1.0, -1.0)},
        {"Component": "FII Surprise", "Value": f"{latest.get('fii_surprise', 0) or 0:.0f} Cr", "Signal": "+1" if (latest.get("fii_surprise") or 0) > 0 else "-1"},
        {"Component": "Futures OI", "Value": f"{latest.get('futures_direction', 0) or 0:+d}", "Signal": f"{latest.get('futures_direction', 0) or 0:+d}"},
        {"Component": "PCR", "Value": f"{latest.get('pcr', 0):.3f}" if latest.get("pcr") else "N/A", "Signal": signal_arrow(latest.get("pcr"), 1.2, 0.7)},
        {"Component": "VIX", "Value": f"{latest.get('vix', 0):.1f}" if latest.get("vix") else "N/A", "Signal": "-1" if latest.get("vix_flag") else "0"},
        {"Component": "S&P 500", "Value": f"{latest.get('sp500_change_pct', 0) or 0:.2f}%", "Signal": f"{latest.get('sp500_direction', 0) or 0:+d}" if latest.get("global_risk_flag") else "0"},
        {"Component": "GIFT Nifty", "Value": f"{latest.get('gift_gap_pct', 0) or 0:.2f}%", "Signal": latest.get("gift_sentiment", "N/A")},
        {"Component": "US Markets", "Value": f"{latest.get('us_avg_chg', 0) or 0:.2f}%", "Signal": latest.get("us_sentiment", "N/A")},
        {"Component": "NIFTY Trend", "Value": f"{latest.get('nifty_5d_chg', 0) or 0:.2f}%", "Signal": latest.get("nifty_trend", "N/A")},
        {"Component": "Fear & Greed", "Value": f"{latest.get('fear_greed_score', 0) or 0:.0f}", "Signal": latest.get("fear_greed_rating", "N/A")},
    ]
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, height=390)

# --- Helper function to format data dates ---
def format_data_date(date_str):
    """Format a data date string (YYYY-MM-DD) for display."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d %b %Y")
    except:
        return date_str

# --- Global Market Indicators ---
st.markdown("---")
st.subheader("Global & Market Indicators")
# Show data dates for global indicators
us_date = format_data_date(latest.get("us_data_date"))
fg_date = format_data_date(latest.get("fg_data_date"))
st.caption(f"US Markets: {us_date} | Fear & Greed: {fg_date}")
glob_col1, glob_col2, glob_col3, glob_col4 = st.columns(4)

with glob_col1:
    gift_sent = latest.get("gift_sentiment", "N/A")
    st.metric(
        "GIFT Nifty (Est. Gap)",
        f"{latest.get('gift_gap_pct', 0) or 0:+.2f}%",
        delta=gift_sent,
        delta_color="normal" if gift_sent == "Positive" else ("inverse" if gift_sent == "Negative" else "off")
    )

with glob_col2:
    us_sent = latest.get("us_sentiment", "N/A")
    st.metric(
        "US Markets",
        f"{latest.get('us_avg_chg', 0) or 0:+.2f}%",
        delta=us_sent,
        delta_color="normal" if us_sent == "Positive" else ("inverse" if us_sent == "Negative" else "off")
    )

with glob_col3:
    fg_score = latest.get("fear_greed_score")
    fg_rating = latest.get("fear_greed_rating", "N/A")
    st.metric(
        "Fear & Greed",
        f"{fg_score:.0f}" if fg_score else "N/A",
        delta=fg_rating.title() if fg_rating else None,
        delta_color="off"
    )

with glob_col4:
    nifty_trend = latest.get("nifty_trend", "N/A")
    rsi = latest.get("nifty_rsi")
    st.metric(
        "NIFTY Trend (5D)",
        f"{latest.get('nifty_5d_chg', 0) or 0:+.2f}%",
        delta=f"RSI: {rsi:.0f}" if rsi else nifty_trend,
        delta_color="off"
    )

# --- Institutional Indicators ---
st.markdown("---")
try:
    date_obj = datetime.strptime(data_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%A, %d %b %Y")
except:
    formatted_date = data_date
st.subheader(f"Institutional Indicators — {formatted_date}")
# Show data dates for institutional indicators
vix_date = format_data_date(latest.get("vix_data_date"))
sp500_date = format_data_date(latest.get("sp500_data_date"))
st.caption(f"NSE Data: {formatted_date} | VIX: {vix_date} | S&P 500: {sp500_date}")
ind_col1, ind_col2, ind_col3 = st.columns(3)

with ind_col1:
    fii_net = latest.get("fii_net")
    dii_net = latest.get("dii_net")
    st.metric("FII Net (Cash)", f"{fii_net:,.0f} Cr" if fii_net else "N/A",
              delta="Buying" if (fii_net or 0) > 0 else "Selling",
              delta_color="normal" if (fii_net or 0) > 0 else "inverse")
    st.metric("DII Net (Cash)", f"{dii_net:,.0f} Cr" if dii_net else "N/A",
              delta="Buying" if (dii_net or 0) > 0 else "Selling",
              delta_color="normal" if (dii_net or 0) > 0 else "inverse")

with ind_col2:
    net_oi = latest.get("fii_net_oi")
    pcr_val = latest.get("pcr")
    st.metric("FII Futures OI (Net)", f"{net_oi:,}" if net_oi else "N/A",
              delta="Long" if (net_oi or 0) > 0 else "Short",
              delta_color="normal" if (net_oi or 0) > 0 else "inverse")
    st.metric("PCR (Near Expiry)", f"{pcr_val:.3f}" if pcr_val else "N/A")

with ind_col3:
    vix_val = latest.get("vix")
    sp_chg = latest.get("sp500_change_pct")
    st.metric("India VIX", f"{vix_val:.2f}" if vix_val else "N/A",
              delta="High Vol" if (vix_val or 0) > 15 else "Normal",
              delta_color="inverse" if (vix_val or 0) > 15 else "off")
    st.metric("S&P 500 Change", f"{sp_chg:+.2f}%" if sp_chg else "N/A")

# --- NIFTY Technical ---
st.markdown("---")
st.subheader("NIFTY Technical")
nifty_date = format_data_date(latest.get("nifty_data_date"))
st.caption(f"Data as of: {nifty_date}")
tech_col1, tech_col2, tech_col3, tech_col4 = st.columns(4)

with tech_col1:
    st.metric("NIFTY 50", f"{latest.get('nifty_price', 0) or 0:,.2f}")
with tech_col2:
    st.metric("5-Day Change", f"{latest.get('nifty_5d_chg', 0) or 0:+.2f}%")
with tech_col3:
    st.metric("20-Day Change", f"{latest.get('nifty_20d_chg', 0) or 0:+.2f}%")
with tech_col4:
    rsi = latest.get("nifty_rsi", 50)
    rsi_label = "Oversold" if rsi < 30 else ("Overbought" if rsi > 70 else "Normal")
    st.metric("RSI (14)", f"{rsi:.1f}", delta=rsi_label,
              delta_color="normal" if rsi < 30 else ("inverse" if rsi > 70 else "off"))

# --- Historical Chart ---
st.markdown("---")
st.subheader(f"Bias Score — Last {chart_days} Days")

history = get_last_n_days(chart_days)

if history.empty or len(history) < 2:
    st.info("Not enough historical data for chart. Run the daily runner for more days.")
else:
    fig = go.Figure()
    colors = history["bias_score"].apply(
        lambda x: "#00C853" if x >= 2 else ("#D32F2F" if x <= -2 else "#9E9E9E")
    )
    fig.add_trace(
        go.Scatter(
            x=history["date"],
            y=history["bias_score"],
            mode="lines+markers",
            line=dict(width=2, color="#42A5F5"),
            marker=dict(color=colors.tolist(), size=9, line=dict(width=1, color="white")),
            hovertemplate="Date: %{x}<br>Score: %{y}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_hrect(y0=2, y1=8, fillcolor="green", opacity=0.05)
    fig.add_hrect(y0=-8, y1=-2, fillcolor="red", opacity=0.05)
    fig.update_layout(
        yaxis_title="Bias Score",
        xaxis_title="Date",
        height=380,
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis=dict(range=[-10, 10], dtick=2),
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.caption(
    "Data: NSE India, Yahoo Finance, CNN Fear & Greed | "
    "10 components: FII Z-score, FII Surprise, Futures OI, PCR, VIX, S&P 500, GIFT Nifty, US Markets, NIFTY Trend, Fear & Greed | "
    "Bias is a directional filter, not an entry signal | "
    "Not investment advice"
)
