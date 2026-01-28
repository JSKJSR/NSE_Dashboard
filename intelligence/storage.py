"""
Intelligence Storage Module
MVP Version - SQLite storage for market events
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Optional
import json

from intelligence.config import INTEL_DB_PATH, EVENT_RETENTION_DAYS

logger = logging.getLogger(__name__)


# Schema for intelligence database
INTEL_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    source TEXT,
    source_type TEXT,
    category TEXT,
    priority REAL,
    priority_level TEXT,
    urgency TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    color TEXT,
    timestamp DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    is_dismissed INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_priority ON events(priority DESC);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
"""


class IntelligenceStorage:
    """SQLite storage for market intelligence events."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or INTEL_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.executescript(INTEL_SCHEMA)

    @contextmanager
    def _get_connection(self):
        """Context-managed database connection."""
        conn = sqlite3.connect(str(self.db_path))
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

    def save_event(self, event: Dict) -> bool:
        """
        Save a classified event to the database.

        Args:
            event: Classified event dictionary

        Returns:
            True if saved, False if duplicate
        """
        try:
            with self._get_connection() as conn:
                # Check if event already exists
                existing = conn.execute(
                    "SELECT id FROM events WHERE id = ?",
                    (event["id"],)
                ).fetchone()

                if existing:
                    return False

                # Extract sentiment data
                sentiment = event.get("sentiment", {})

                conn.execute("""
                    INSERT INTO events (
                        id, headline, summary, url, source, source_type,
                        category, priority, priority_level, urgency,
                        sentiment_score, sentiment_label, color, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["id"],
                    event.get("headline", ""),
                    event.get("summary", ""),
                    event.get("url", ""),
                    event.get("source", ""),
                    event.get("source_type", ""),
                    event.get("category", "GENERAL"),
                    event.get("priority", 0),
                    event.get("priority_level", "LOW"),
                    event.get("urgency", "normal"),
                    sentiment.get("score", 0),
                    sentiment.get("label", "neutral"),
                    event.get("color", "#808080"),
                    event.get("timestamp", datetime.now())
                ))

                return True

        except Exception as e:
            logger.error(f"Error saving event: {e}")
            return False

    def save_events(self, events: List[Dict]) -> int:
        """
        Save multiple events.

        Returns:
            Number of new events saved
        """
        saved = 0
        for event in events:
            if self.save_event(event):
                saved += 1
        return saved

    def get_recent_events(
        self,
        limit: int = 20,
        hours: int = 24,
        min_priority: Optional[float] = None,
        category: Optional[str] = None,
        include_dismissed: bool = False
    ) -> List[Dict]:
        """
        Get recent events with optional filters.

        Args:
            limit: Maximum number of events to return
            hours: Look back this many hours
            min_priority: Minimum priority score filter
            category: Filter by category
            include_dismissed: Include dismissed events

        Returns:
            List of event dictionaries
        """
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT * FROM events
                    WHERE timestamp > datetime('now', ?)
                """
                params = [f'-{hours} hours']

                if not include_dismissed:
                    query += " AND is_dismissed = 0"

                if min_priority is not None:
                    query += " AND priority >= ?"
                    params.append(min_priority)

                if category:
                    query += " AND category = ?"
                    params.append(category)

                query += " ORDER BY priority DESC, timestamp DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(query, params).fetchall()

                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []

    def get_critical_events(self, hours: int = 6) -> List[Dict]:
        """Get critical priority events from recent hours."""
        return self.get_recent_events(
            limit=10,
            hours=hours,
            min_priority=80
        )

    def get_events_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Get events of a specific category."""
        return self.get_recent_events(
            limit=limit,
            category=category
        )

    def mark_as_read(self, event_id: str):
        """Mark an event as read."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE events SET is_read = 1 WHERE id = ?",
                    (event_id,)
                )
        except Exception as e:
            logger.error(f"Error marking event as read: {e}")

    def dismiss_event(self, event_id: str):
        """Dismiss an event (hide from default view)."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE events SET is_dismissed = 1 WHERE id = ?",
                    (event_id,)
                )
        except Exception as e:
            logger.error(f"Error dismissing event: {e}")

    def cleanup_old_events(self, days: Optional[int] = None):
        """Remove events older than retention period."""
        days = days or EVENT_RETENTION_DAYS
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM events WHERE timestamp < datetime('now', ?)",
                    (f'-{days} days',)
                )
                logger.info(f"Cleaned up events older than {days} days")
        except Exception as e:
            logger.error(f"Error cleaning up events: {e}")

    def get_event_counts(self, hours: int = 24) -> Dict:
        """Get event counts by category and priority."""
        try:
            with self._get_connection() as conn:
                # Count by category
                category_counts = conn.execute("""
                    SELECT category, COUNT(*) as count
                    FROM events
                    WHERE timestamp > datetime('now', ?)
                    GROUP BY category
                """, (f'-{hours} hours',)).fetchall()

                # Count by priority level
                priority_counts = conn.execute("""
                    SELECT priority_level, COUNT(*) as count
                    FROM events
                    WHERE timestamp > datetime('now', ?)
                    GROUP BY priority_level
                """, (f'-{hours} hours',)).fetchall()

                # Total count
                total = conn.execute("""
                    SELECT COUNT(*) FROM events
                    WHERE timestamp > datetime('now', ?)
                """, (f'-{hours} hours',)).fetchone()[0]

                return {
                    "total": total,
                    "by_category": {row["category"]: row["count"] for row in category_counts},
                    "by_priority": {row["priority_level"]: row["count"] for row in priority_counts}
                }

        except Exception as e:
            logger.error(f"Error getting event counts: {e}")
            return {"total": 0, "by_category": {}, "by_priority": {}}

    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary."""
        return {
            "id": row["id"],
            "headline": row["headline"],
            "summary": row["summary"],
            "url": row["url"],
            "source": row["source"],
            "source_type": row["source_type"],
            "category": row["category"],
            "priority": row["priority"],
            "priority_level": row["priority_level"],
            "urgency": row["urgency"],
            "sentiment": {
                "score": row["sentiment_score"],
                "label": row["sentiment_label"]
            },
            "color": row["color"],
            "timestamp": row["timestamp"],
            "is_read": bool(row["is_read"]),
            "is_dismissed": bool(row["is_dismissed"])
        }


# Singleton instance
_storage = None


def get_storage() -> IntelligenceStorage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = IntelligenceStorage()
    return _storage
