"""Collect alerts from oref API and store in SQLite for 24h history."""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .oref_client import Alert, fetch_alerts

logger = logging.getLogger(__name__)

ISRAEL_TZ = timezone(timedelta(hours=3))
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "alerts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    category INTEGER NOT NULL,
    category_desc TEXT NOT NULL,
    is_night INTEGER NOT NULL,
    UNIQUE(area, timestamp, category)
);
CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp);
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class AlertStore:
    """SQLite-backed alert store with dedup and auto-pruning."""

    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    def store(self, alerts: list[Alert]) -> int:
        """Store alerts, skipping duplicates. Returns count of new alerts added."""
        added = 0
        with sqlite3.connect(self.db_path) as conn:
            for alert in alerts:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO alerts (area, timestamp, category, category_desc, is_night) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            alert.area,
                            alert.timestamp.isoformat(),
                            alert.category,
                            alert.category_desc,
                            1 if alert.is_night else 0,
                        ),
                    )
                    if conn.total_changes > added:
                        added = conn.total_changes
                except sqlite3.Error as e:
                    logger.warning("Failed to store alert: %s", e)
        logger.info("Stored %d new alerts (of %d fetched)", added, len(alerts))
        return added

    def get_alerts(
        self,
        lookback_hours: int = 24,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Alert]:
        """Retrieve alerts for a time window.

        If since/until are provided, they take precedence over lookback_hours.
        """
        if since and until:
            cutoff_str = since.isoformat()
            until_str = until.isoformat()
        else:
            cutoff = datetime.now(ISRAEL_TZ) - timedelta(hours=lookback_hours)
            cutoff_str = cutoff.isoformat()
            until_str = None

        with sqlite3.connect(self.db_path) as conn:
            if until_str:
                rows = conn.execute(
                    "SELECT area, timestamp, category, category_desc, is_night "
                    "FROM alerts WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                    (cutoff_str, until_str),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT area, timestamp, category, category_desc, is_night "
                    "FROM alerts WHERE timestamp >= ? ORDER BY timestamp",
                    (cutoff_str,),
                ).fetchall()

        alerts = []
        for area, ts_str, category, category_desc, is_night in rows:
            ts = datetime.fromisoformat(ts_str)
            alerts.append(Alert(
                area=area,
                timestamp=ts,
                category=category,
                category_desc=category_desc,
                is_night=bool(is_night),
            ))
        logger.info("Retrieved %d alerts from db (cutoff=%s)", len(alerts), cutoff_str)
        return alerts

    def prune(self, keep_hours: int = 48) -> int:
        """Delete alerts older than keep_hours. Returns count deleted."""
        cutoff = datetime.now(ISRAEL_TZ) - timedelta(hours=keep_hours)
        cutoff_str = cutoff.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff_str,))
            deleted = cursor.rowcount
        if deleted:
            logger.info("Pruned %d alerts older than %dh", deleted, keep_hours)
        return deleted

    def count(self) -> int:
        """Total alerts in the database."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    def get_state(self, key: str) -> str | None:
        """Read a value from the state table."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None

    def set_state(self, key: str, value: str) -> None:
        """Write a value to the state table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, value),
            )


def run_collect(
    categories: list[int] | None = None,
    night_start: int = 22,
    night_end: int = 7,
    db_path: Path | str = DEFAULT_DB,
) -> None:
    """Fetch latest alerts from oref API and store in SQLite."""
    store = AlertStore(db_path)

    # Fetch with a wide lookback — the API returns whatever it has (up to 3000 records).
    # Dedup in SQLite handles overlap with previous polls.
    alerts = fetch_alerts(
        lookback_hours=24,
        categories=categories,
        night_start=night_start,
        night_end=night_end,
    )

    store.store(alerts)
    store.prune(keep_hours=48)

    # Prune old subscriber report records
    from .subscribers import SubscriberStore
    try:
        sub_store = SubscriberStore(db_path)
        sub_store.prune_reports(days=30)
    except sqlite3.OperationalError:
        logger.debug("Subscriber report pruning skipped (table may not exist yet)")

    logger.info("Collection complete. DB has %d alerts total.", store.count())
