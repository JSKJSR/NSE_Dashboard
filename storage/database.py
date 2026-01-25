import sqlite3
from contextlib import contextmanager

from config.settings import DB_PATH
from storage.models import (
    SCHEMA_DAILY_DATA,
    SCHEMA_FETCH_LOG,
    INDEX_DAILY_DATE,
    MIGRATION_NEW_COLUMNS,
)


def init_db():
    """Create tables if they don't exist, and run migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            SCHEMA_DAILY_DATA + SCHEMA_FETCH_LOG + INDEX_DAILY_DATE
        )
        # Run migration to add new columns
        _migrate_add_columns(conn)


def _migrate_add_columns(conn):
    """Add new columns to existing table if they don't exist."""
    # Get existing columns
    cursor = conn.execute("PRAGMA table_info(daily_data)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # Add missing columns
    for col_name, col_type in MIGRATION_NEW_COLUMNS:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE daily_data ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists


@contextmanager
def get_connection():
    """Context-managed SQLite connection with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
