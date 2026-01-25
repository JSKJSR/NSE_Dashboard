#!/usr/bin/env python3
"""
NIFTY Daily Institutional Bias Dashboard — Streamlit App.

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
    """Run the daily data fetch pipeline."""
    from fetchers.nse_fiidii import fetch_fiidii
    from fetchers.nse_futures_oi import fetch_futures_oi
    from fetchers.nse_option_chain import fetch_option_chain_pcr
    from fetchers.nse_vix import fetch_vix
    from fetchers.sp500 import fetch_sp500
    from core.features import compute_features
    from core.bias_engine import compute_bias
    from storage.queries import insert_daily_row, get_last_n_rows

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    data_complete = 1
    raw = {"date": date_str}
    status_messages = []

    # Fetch all sources
    with st.spinner("Fetching FII/DII data..."):
        fiidii = fetch_fiidii()
        if fiidii:
            raw.update(fiidii)
            status_messages.append(f"FII/DII: FII={fiidii.get('fii_net'):,.0f} Cr")
        else:
            data_complete = 0
            status_messages.append("FII/DII: Failed")

    with st.spinner("Fetching Futures OI..."):
        oi_date_str = today.strftime("%d%m%Y")
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
            data_complete = 0
            status_messages.append("PCR: Failed (market may be closed)")

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
            status_messages.append("S&P 500: Failed (using neutral)")

    # Compute features and bias
    with st.spinner("Computing bias..."):
        history = get_last_n_rows(20)
        features = compute_features(raw, history)
        score, label, guidance = compute_bias(features, raw)

    # Store
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

# Check if today's data exists
today_str = datetime.now().strftime("%Y-%m-%d")
has_today = date_exists(today_str)

if has_today:
    st.sidebar.success(f"Today's data loaded")
else:
    st.sidebar.warning("No data for today")

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


# --- Helper ---
def bias_color(label: str) -> str:
    colors = {
        "Strong Bullish": "#00C853",
        "Bullish": "#66BB6A",
        "Neutral": "#9E9E9E",
        "Bearish": "#FF7043",
        "Strong Bearish": "#D32F2F",
    }
    return colors.get(label, "#9E9E9E")


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
    st.info("Click **Fetch Now** in the sidebar to load today's data, or run locally:\n\n```\npython scheduler/daily_runner.py\n```")

    # Also show a big fetch button in main area for convenience
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
    score = latest.get("bias_score", 0)
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
    st.markdown(f"**Date:** {latest.get('date', 'N/A')}")
    st.markdown(f"**Updated:** {latest.get('fetch_timestamp', 'N/A')[:19]}")
    if latest.get("data_complete") == 0:
        st.warning("Some data sources failed. Bias may be less reliable.")

with col3:
    st.markdown("**Score Breakdown**")
    breakdown_data = [
        {
            "Component": "FII Z-score",
            "Value": f"{latest.get('fii_zscore', 0):.2f}",
            "Signal": signal_arrow(latest.get("fii_zscore"), 1.0, -1.0),
        },
        {
            "Component": "FII Surprise",
            "Value": f"{latest.get('fii_surprise', 0):.0f} Cr",
            "Signal": "+1" if (latest.get("fii_surprise") or 0) > 0 else "-1",
        },
        {
            "Component": "Futures OI",
            "Value": f"{latest.get('futures_direction', 0):+d}",
            "Signal": f"{latest.get('futures_direction', 0):+d}",
        },
        {
            "Component": "PCR",
            "Value": f"{latest.get('pcr', 0):.3f}" if latest.get("pcr") else "N/A",
            "Signal": signal_arrow(latest.get("pcr"), 1.2, 0.7),
        },
        {
            "Component": "VIX",
            "Value": f"{latest.get('vix', 0):.1f}" if latest.get("vix") else "N/A",
            "Signal": "-1" if latest.get("vix_flag") else "0",
        },
        {
            "Component": "S&P 500",
            "Value": f"{latest.get('sp500_change_pct', 0):.2f}%",
            "Signal": f"{latest.get('sp500_direction', 0):+d}" if latest.get("global_risk_flag") else "0",
        },
    ]
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, width="stretch")

# --- Indicators Section ---
st.markdown("---")
st.subheader("Today's Indicators")
ind_col1, ind_col2, ind_col3 = st.columns(3)

with ind_col1:
    fii_net = latest.get("fii_net")
    dii_net = latest.get("dii_net")
    st.metric("FII Net (Cash)", f"{fii_net:,.0f} Cr" if fii_net else "N/A")
    st.metric("DII Net (Cash)", f"{dii_net:,.0f} Cr" if dii_net else "N/A")

with ind_col2:
    net_oi = latest.get("fii_net_oi")
    pcr_val = latest.get("pcr")
    st.metric("FII Futures OI (Net)", f"{net_oi:,}" if net_oi else "N/A")
    st.metric("PCR (Near Expiry)", f"{pcr_val:.3f}" if pcr_val else "N/A")

with ind_col3:
    vix_val = latest.get("vix")
    sp_chg = latest.get("sp500_change_pct")
    st.metric("India VIX", f"{vix_val:.2f}" if vix_val else "N/A")
    st.metric("S&P 500 Change", f"{sp_chg:+.2f}%" if sp_chg else "N/A")

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
    fig.add_hrect(y0=2, y1=5, fillcolor="green", opacity=0.05)
    fig.add_hrect(y0=-5, y1=-2, fillcolor="red", opacity=0.05)
    fig.update_layout(
        yaxis_title="Bias Score",
        xaxis_title="Date",
        height=380,
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis=dict(range=[-6, 6], dtick=1),
    )
    st.plotly_chart(fig, width="stretch")

# --- Footer ---
st.markdown("---")
st.caption(
    "Data: NSE India, Yahoo Finance | "
    "Bias is a directional filter, not an entry signal | "
    "Not investment advice"
)
