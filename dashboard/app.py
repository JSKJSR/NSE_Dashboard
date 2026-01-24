#!/usr/bin/env python3
"""
NIFTY Daily Institutional Bias Dashboard — Streamlit App.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from storage.database import init_db
from storage.queries import get_latest_row, get_last_n_days

# --- Page Config ---
st.set_page_config(
    page_title="NIFTY Bias Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize DB (creates tables if needed)
init_db()

# --- Sidebar ---
st.sidebar.title("Settings")
refresh_seconds = st.sidebar.selectbox(
    "Auto-refresh interval",
    options=[0, 30, 60, 300],
    format_func=lambda x: "Off" if x == 0 else f"{x}s",
    index=0,
)
chart_days = st.sidebar.slider("Chart history (days)", 7, 90, 30)

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
    st.warning(
        "No data available yet. Run the daily runner first:\n\n"
        "```\npython scheduler/daily_runner.py\n```"
    )
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
