"""SQLite-backed subscriber store for personalized alert reports."""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .city_names import CITY_REGIONS

logger = logging.getLogger(__name__)

ISRAEL_TZ = timezone(timedelta(hours=3))
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "alerts.db"
LEGACY_JSON = Path(__file__).resolve().parent.parent / "data" / "subscribers.json"

SUBSCRIBER_SCHEMA = """
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    region TEXT
);

CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    webhook_url TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriber_cities (
    subscriber_id INTEGER REFERENCES subscribers(id) ON DELETE CASCADE,
    city_id INTEGER REFERENCES cities(id),
    PRIMARY KEY (subscriber_id, city_id)
);

CREATE TABLE IF NOT EXISTS subscriber_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id INTEGER REFERENCES subscribers(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL,
    report_date TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(subscriber_id, report_type, report_date)
);
"""


@dataclass
class Subscriber:
    """A subscriber who receives filtered reports for specific cities."""
    id: int
    name: str
    webhook_url: str
    cities: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class SubscriberStore:
    """SQLite-backed subscriber management."""

    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.seed_cities()
        self._migrate_json()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SUBSCRIBER_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def seed_cities(self) -> None:
        """Seed the cities table from city_names.py. Idempotent."""
        with self._connect() as conn:
            for name, region in CITY_REGIONS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO cities (name, region) VALUES (?, ?)",
                    (name, region),
                )

    def _migrate_json(self) -> None:
        """Import subscribers from legacy JSON file if it exists."""
        json_path = LEGACY_JSON if self.db_path == DEFAULT_DB else None
        if json_path and json_path.exists():
            try:
                data = json.loads(json_path.read_text())
                if isinstance(data, list):
                    for entry in data:
                        name = entry.get("name", "")
                        webhook_url = entry.get("webhook_url", "")
                        cities = entry.get("cities", [])
                        if name and webhook_url and cities:
                            try:
                                self.add(name, webhook_url, cities)
                                logger.info("Migrated subscriber '%s' from JSON", name)
                            except ValueError:
                                logger.debug("Subscriber '%s' already exists, skipping", name)
                json_path.rename(json_path.with_suffix(".json.migrated"))
                logger.info("Migrated subscribers from %s", json_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to migrate subscribers JSON: %s", e)

    def _now_iso(self) -> str:
        return datetime.now(ISRAEL_TZ).isoformat()

    def _get_or_create_city_id(self, conn: sqlite3.Connection, city_name: str) -> int:
        """Get city ID, creating the city if it doesn't exist."""
        row = conn.execute("SELECT id FROM cities WHERE name = ?", (city_name,)).fetchone()
        if row:
            return row[0]
        # Unknown city — insert with no region
        cursor = conn.execute("INSERT INTO cities (name, region) VALUES (?, NULL)", (city_name,))
        return cursor.lastrowid

    def add(self, name: str, webhook_url: str, cities: list[str]) -> Subscriber:
        """Add a subscriber. Raises ValueError if name already exists."""
        now = self._now_iso()
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO subscribers (name, webhook_url, enabled, created_at, updated_at) "
                    "VALUES (?, ?, 1, ?, ?)",
                    (name, webhook_url, now, now),
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"Subscriber '{name}' already exists")

            sub_id = cursor.lastrowid

            for city in cities:
                city_id = self._get_or_create_city_id(conn, city)
                conn.execute(
                    "INSERT OR IGNORE INTO subscriber_cities (subscriber_id, city_id) VALUES (?, ?)",
                    (sub_id, city_id),
                )

        logger.info("Added subscriber '%s' (id=%d) with %d cities", name, sub_id, len(cities))
        return Subscriber(
            id=sub_id, name=name, webhook_url=webhook_url,
            cities=cities, enabled=True, created_at=now, updated_at=now,
        )

    def remove(self, name: str) -> None:
        """Remove a subscriber by name. Raises KeyError if not found."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM subscribers WHERE name = ?", (name,))
            if cursor.rowcount == 0:
                raise KeyError(f"Subscriber '{name}' not found")
        logger.info("Removed subscriber '%s'", name)

    def update(
        self, name: str, webhook_url: str | None = None, cities: list[str] | None = None
    ) -> None:
        """Update a subscriber's webhook URL and/or cities. Raises KeyError if not found."""
        now = self._now_iso()
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM subscribers WHERE name = ?", (name,)).fetchone()
            if not row:
                raise KeyError(f"Subscriber '{name}' not found")
            sub_id = row[0]

            if webhook_url is not None:
                conn.execute(
                    "UPDATE subscribers SET webhook_url = ?, updated_at = ? WHERE id = ?",
                    (webhook_url, now, sub_id),
                )

            if cities is not None:
                conn.execute("DELETE FROM subscriber_cities WHERE subscriber_id = ?", (sub_id,))
                for city in cities:
                    city_id = self._get_or_create_city_id(conn, city)
                    conn.execute(
                        "INSERT OR IGNORE INTO subscriber_cities (subscriber_id, city_id) VALUES (?, ?)",
                        (sub_id, city_id),
                    )
                conn.execute(
                    "UPDATE subscribers SET updated_at = ? WHERE id = ?", (now, sub_id),
                )

        logger.info("Updated subscriber '%s'", name)

    def enable(self, name: str) -> None:
        """Enable a subscriber. Raises KeyError if not found."""
        self._set_enabled(name, True)

    def disable(self, name: str) -> None:
        """Disable a subscriber. Raises KeyError if not found."""
        self._set_enabled(name, False)

    def _set_enabled(self, name: str, enabled: bool) -> None:
        now = self._now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE subscribers SET enabled = ?, updated_at = ? WHERE name = ?",
                (1 if enabled else 0, now, name),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Subscriber '{name}' not found")
        logger.info("%s subscriber '%s'", "Enabled" if enabled else "Disabled", name)

    def _load_subscribers(self, conn: sqlite3.Connection, where: str = "", params: tuple = ()) -> list[Subscriber]:
        """Load subscribers with cities in a single query."""
        rows = conn.execute(
            "SELECT s.id, s.name, s.webhook_url, s.enabled, s.created_at, s.updated_at, "
            "GROUP_CONCAT(c.name, '||') "
            "FROM subscribers s "
            "LEFT JOIN subscriber_cities sc ON s.id = sc.subscriber_id "
            "LEFT JOIN cities c ON sc.city_id = c.id "
            + (f"WHERE {where} " if where else "")
            + "GROUP BY s.id ORDER BY s.id",
            params,
        ).fetchall()
        subscribers = []
        for sub_id, name, webhook_url, enabled, created_at, updated_at, cities_str in rows:
            cities = sorted(cities_str.split("||")) if cities_str else []
            subscribers.append(Subscriber(
                id=sub_id, name=name, webhook_url=webhook_url,
                cities=cities, enabled=bool(enabled),
                created_at=created_at, updated_at=updated_at,
            ))
        return subscribers

    def list_all(self) -> list[Subscriber]:
        """Return all subscribers."""
        with self._connect() as conn:
            return self._load_subscribers(conn)

    def get_enabled(self) -> list[Subscriber]:
        """Return only enabled subscribers."""
        with self._connect() as conn:
            return self._load_subscribers(conn, where="s.enabled = 1")

    def record_report_sent(
        self, subscriber_id: int, report_type: str, report_date: str
    ) -> None:
        """Record that a report was sent to a subscriber."""
        sent_at = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO subscriber_reports "
                "(subscriber_id, report_type, report_date, sent_at) VALUES (?, ?, ?, ?)",
                (subscriber_id, report_type, report_date, sent_at),
            )

    def was_report_sent(
        self, subscriber_id: int, report_type: str, report_date: str
    ) -> bool:
        """Check if a report was already sent to a subscriber for a given date."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM subscriber_reports "
                "WHERE subscriber_id = ? AND report_type = ? AND report_date = ?",
                (subscriber_id, report_type, report_date),
            ).fetchone()
            return row is not None

    def get_reports_sent_count(self, subscriber_id: int) -> int:
        """Get total number of reports sent to a subscriber."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM subscriber_reports WHERE subscriber_id = ?",
                (subscriber_id,),
            ).fetchone()
            return row[0]

    def prune_reports(self, days: int = 30) -> int:
        """Delete subscriber_reports older than N days. Returns count deleted."""
        cutoff = (datetime.now(ISRAEL_TZ) - timedelta(days=days)).date().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM subscriber_reports WHERE report_date < ?", (cutoff,)
            )
            deleted = cursor.rowcount
        if deleted:
            logger.info("Pruned %d subscriber report records older than %d days", deleted, days)
        return deleted
