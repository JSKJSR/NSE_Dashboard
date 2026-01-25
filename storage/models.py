SCHEMA_DAILY_DATA = """
CREATE TABLE IF NOT EXISTS daily_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,

    -- Raw fetched data (FII/DII)
    fii_buy REAL,
    fii_sell REAL,
    fii_net REAL,
    dii_buy REAL,
    dii_sell REAL,
    dii_net REAL,

    -- Futures OI
    fii_long_oi INTEGER,
    fii_short_oi INTEGER,
    fii_net_oi INTEGER,

    -- Options / PCR
    pcr REAL,
    total_ce_oi INTEGER,
    total_pe_oi INTEGER,

    -- VIX
    vix REAL,

    -- S&P 500
    sp500_close REAL,
    sp500_change_pct REAL,

    -- GIFT Nifty / Pre-market
    gift_nifty REAL,
    gift_gap_pct REAL,
    gift_sentiment TEXT,

    -- US Markets
    us_sentiment TEXT,
    us_avg_chg REAL,
    dow_chg REAL,
    nasdaq_chg REAL,

    -- NIFTY Trend
    nifty_price REAL,
    nifty_5d_chg REAL,
    nifty_20d_chg REAL,
    nifty_rsi REAL,
    nifty_trend TEXT,
    nifty_trend_score INTEGER,

    -- Fear & Greed
    fear_greed_score REAL,
    fear_greed_rating TEXT,
    fear_greed_signal INTEGER,

    -- Computed features
    fii_zscore REAL,
    fii_surprise REAL,
    dii_surprise REAL,
    futures_direction INTEGER,
    pcr_change REAL,
    vix_flag INTEGER,
    global_risk_flag INTEGER,
    sp500_direction INTEGER,

    -- Bias result
    bias_score INTEGER,
    bias_label TEXT,
    bias_guidance TEXT,

    -- Data source dates
    sp500_data_date TEXT,
    us_data_date TEXT,
    nifty_data_date TEXT,
    gift_data_date TEXT,
    fg_data_date TEXT,
    vix_data_date TEXT,

    -- Metadata
    fetch_timestamp TEXT,
    data_complete INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# Migration: Add new columns to existing table
MIGRATION_NEW_COLUMNS = [
    ("gift_nifty", "REAL"),
    ("gift_gap_pct", "REAL"),
    ("gift_sentiment", "TEXT"),
    ("us_sentiment", "TEXT"),
    ("us_avg_chg", "REAL"),
    ("dow_chg", "REAL"),
    ("nasdaq_chg", "REAL"),
    ("nifty_price", "REAL"),
    ("nifty_5d_chg", "REAL"),
    ("nifty_20d_chg", "REAL"),
    ("nifty_rsi", "REAL"),
    ("nifty_trend", "TEXT"),
    ("nifty_trend_score", "INTEGER"),
    ("fear_greed_score", "REAL"),
    ("fear_greed_rating", "TEXT"),
    ("fear_greed_signal", "INTEGER"),
    # Data source dates (actual trading day of the data)
    ("sp500_data_date", "TEXT"),
    ("us_data_date", "TEXT"),
    ("nifty_data_date", "TEXT"),
    ("gift_data_date", "TEXT"),
    ("fg_data_date", "TEXT"),
    ("vix_data_date", "TEXT"),
]

SCHEMA_FETCH_LOG = """
CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

INDEX_DAILY_DATE = """
CREATE INDEX IF NOT EXISTS idx_daily_data_date ON daily_data(date);
"""
