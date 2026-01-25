# NIFTY Daily Institutional Bias Dashboard

Auto-updating dashboard that computes a daily **NIFTY market bias** based on institutional activity.

## Data Sources

| Indicator | Source |
|-----------|--------|
| FII/DII Cash Market | NSE India |
| FII Index Futures OI | NSE Participant Data |
| Put-Call Ratio (PCR) | NSE Option Chain |
| India VIX | NSE |
| Global Risk Cue | S&P 500 (Yahoo Finance) |

## Bias Score Components

The bias score (-5 to +5) is computed from 6 components:

1. **FII Z-score** — Is FII buying/selling significantly above/below 20-day average?
2. **FII Cash Surprise** — Did FII buy more or less than expected?
3. **Futures OI Direction** — Are FII adding longs or shorts?
4. **PCR Level** — High PCR (>1.2) = bullish, Low PCR (<0.7) = bearish
5. **VIX Regime** — VIX > 15 adds bearish pressure
6. **Global Risk** — Large S&P 500 moves (>0.7%) influence bias direction

## Labels

| Score | Label |
|-------|-------|
| +4 to +5 | Strong Bullish |
| +2 to +3 | Bullish |
| -1 to +1 | Neutral |
| -2 to -3 | Bearish |
| -4 to -5 | Strong Bearish |

## Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch today's data
python scheduler/daily_runner.py

# Run dashboard
streamlit run dashboard/app.py
```

## macOS App Launcher

Double-click `launcher/NSE_Bias_Dashboard.app` to:
1. Fetch latest data
2. Start Streamlit server
3. Open browser to dashboard

Use `./launcher/stop_dashboard.sh` to stop.

## Auto-scheduling (macOS)

```bash
cp scheduler/com.nse.bias-dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nse.bias-dashboard.plist
```

Runs daily at 4:15 PM IST after market close.

---

**Disclaimer**: This is a directional filter, not an entry signal. Not investment advice.
