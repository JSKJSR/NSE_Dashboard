import pandas as pd
from storage.database import get_connection


def insert_daily_row(data: dict):
    """Insert or replace a daily data row."""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT OR REPLACE INTO daily_data ({columns}) VALUES ({placeholders})"
    with get_connection() as conn:
        conn.execute(sql, list(data.values()))


def insert_fetch_log(date: str, source: str, status: str,
                     attempts: int = 1, error_message: str = None):
    """Log a fetch attempt."""
    sql = """INSERT INTO fetch_log (date, source, status, attempts, error_message)
             VALUES (?, ?, ?, ?, ?)"""
    with get_connection() as conn:
        conn.execute(sql, (date, source, status, attempts, error_message))


def get_last_n_rows(n: int) -> pd.DataFrame:
    """Get the last N rows of daily_data ordered by date ascending."""
    sql = f"""SELECT * FROM daily_data ORDER BY date DESC LIMIT {n}"""
    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn)
    return df.sort_values("date").reset_index(drop=True)


def get_latest_row() -> dict | None:
    """Get the most recent daily_data row as a dict."""
    sql = "SELECT * FROM daily_data ORDER BY date DESC LIMIT 1"
    with get_connection() as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        return None
    return dict(row)


def get_last_n_days(n: int) -> pd.DataFrame:
    """Get the last N days for charting."""
    return get_last_n_rows(n)


def date_exists(date: str) -> bool:
    """Check if a date already has data."""
    sql = "SELECT 1 FROM daily_data WHERE date = ? LIMIT 1"
    with get_connection() as conn:
        result = conn.execute(sql, (date,)).fetchone()
    return result is not None
