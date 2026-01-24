SCHEMA_DAILY_DATA = """
CREATE TABLE IF NOT EXISTS daily_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,

    -- Raw fetched data
    fii_buy REAL,
    fii_sell REAL,
    fii_net REAL,
    dii_buy REAL,
    dii_sell REAL,
    dii_net REAL,

    fii_long_oi INTEGER,
    fii_short_oi INTEGER,
    fii_net_oi INTEGER,

    pcr REAL,
    total_ce_oi INTEGER,
    total_pe_oi INTEGER,

    vix REAL,

    sp500_close REAL,
    sp500_change_pct REAL,

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

    -- Metadata
    fetch_timestamp TEXT,
    data_complete INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

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
