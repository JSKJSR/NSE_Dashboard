from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "data" / "nse_bias.db"
LOG_DIR = PROJECT_DIR / "logs"

# Rolling windows
ROLLING_WINDOW = 20  # days for z-score and rolling mean

# Bias thresholds
FII_ZSCORE_THRESHOLD = 1.0
VIX_HIGH_THRESHOLD = 15.0
SP500_MOVE_THRESHOLD = 0.7  # percent
PCR_BULL_THRESHOLD = 1.2
PCR_BEAR_THRESHOLD = 0.7

# NSE fetch settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds (linear backoff multiplier)
REQUEST_TIMEOUT = 15
