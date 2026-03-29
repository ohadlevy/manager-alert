"""Tests for SQLite-backed subscriber store."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from manager_alert.subscribers import Subscriber, SubscriberStore

ISRAEL_TZ = timezone(timedelta(hours=3))


@pytest.fixture
def store(tmp_path):
    db = tmp_path / "test.db"
    return SubscriberStore(db_path=db)


class TestAdd:
    def test_add_subscriber(self, store):
        sub = store.add("Backend Team", "https://hooks.example.com/1", ["Tel Aviv", "Haifa"])
        assert sub.name == "Backend Team"
        assert sub.cities == ["Tel Aviv", "Haifa"]
        assert sub.enabled is True
        assert sub.id > 0

    def test_duplicate_name_raises(self, store):
        store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        with pytest.raises(ValueError, match="already exists"):
            store.add("Team A", "https://hooks.example.com/2", ["Tel Aviv"])

    def test_unknown_city_allowed(self, store):
        sub = store.add("Team X", "https://hooks.example.com/1", ["Some Village"])
        assert sub.cities == ["Some Village"]


class TestRemove:
    def test_remove_subscriber(self, store):
        store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.remove("Team A")
        assert store.list_all() == []

    def test_remove_missing_raises(self, store):
        with pytest.raises(KeyError, match="not found"):
            store.remove("Nobody")

    def test_cascade_deletes_cities_and_reports(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        store.remove("Team A")
        # Verify join table and reports are cleaned up
        with sqlite3.connect(store.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            sc_count = conn.execute("SELECT COUNT(*) FROM subscriber_cities").fetchone()[0]
            sr_count = conn.execute("SELECT COUNT(*) FROM subscriber_reports").fetchone()[0]
        assert sc_count == 0
        assert sr_count == 0


class TestUpdate:
    def test_update_cities(self, store):
        store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.update("Team A", cities=["Tel Aviv", "Ra'anana"])
        subs = store.list_all()
        assert sorted(subs[0].cities) == ["Ra'anana", "Tel Aviv"]

    def test_update_webhook(self, store):
        store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.update("Team A", webhook_url="https://hooks.example.com/new")
        subs = store.list_all()
        assert subs[0].webhook_url == "https://hooks.example.com/new"

    def test_update_missing_raises(self, store):
        with pytest.raises(KeyError, match="not found"):
            store.update("Nobody", cities=["Haifa"])


class TestEnableDisable:
    def test_disable_and_enable(self, store):
        store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.disable("Team A")
        assert store.get_enabled() == []
        assert len(store.list_all()) == 1
        assert store.list_all()[0].enabled is False

        store.enable("Team A")
        assert len(store.get_enabled()) == 1
        assert store.get_enabled()[0].enabled is True

    def test_disable_missing_raises(self, store):
        with pytest.raises(KeyError, match="not found"):
            store.disable("Nobody")


class TestList:
    def test_list_all(self, store):
        store.add("A", "https://a.com", ["Haifa"])
        store.add("B", "https://b.com", ["Tel Aviv"])
        subs = store.list_all()
        assert len(subs) == 2
        assert subs[0].name == "A"
        assert subs[1].name == "B"

    def test_get_enabled_filters_disabled(self, store):
        store.add("A", "https://a.com", ["Haifa"])
        store.add("B", "https://b.com", ["Tel Aviv"])
        store.disable("B")
        enabled = store.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "A"


class TestReportTracking:
    def test_was_report_sent(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        assert not store.was_report_sent(sub.id, "overnight", "2026-03-29")
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        assert store.was_report_sent(sub.id, "overnight", "2026-03-29")

    def test_different_report_types_independent(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        assert not store.was_report_sent(sub.id, "daytime", "2026-03-29")

    def test_different_dates_independent(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        assert not store.was_report_sent(sub.id, "overnight", "2026-03-30")

    def test_reports_sent_count(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        assert store.get_reports_sent_count(sub.id) == 0
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        store.record_report_sent(sub.id, "daytime", "2026-03-29")
        assert store.get_reports_sent_count(sub.id) == 2

    def test_duplicate_record_ignored(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.record_report_sent(sub.id, "overnight", "2026-03-29")
        store.record_report_sent(sub.id, "overnight", "2026-03-29")  # dupe
        assert store.get_reports_sent_count(sub.id) == 1


class TestPruneReports:
    def test_prune_old_reports(self, store):
        sub = store.add("Team A", "https://hooks.example.com/1", ["Haifa"])
        store.record_report_sent(sub.id, "overnight", "2026-01-01")  # old
        store.record_report_sent(sub.id, "overnight", "2026-03-29")  # recent
        deleted = store.prune_reports(days=30)
        assert deleted == 1
        assert store.get_reports_sent_count(sub.id) == 1


class TestSeedCities:
    def test_cities_seeded(self, store):
        with sqlite3.connect(store.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        assert count > 50  # we have ~80 cities in CITY_REGIONS

    def test_seed_idempotent(self, store):
        with sqlite3.connect(store.db_path) as conn:
            count1 = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        store.seed_cities()
        with sqlite3.connect(store.db_path) as conn:
            count2 = conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
        assert count1 == count2


class TestJsonMigration:
    def test_migrate_from_json(self, tmp_path):
        # Set up legacy JSON file
        json_path = tmp_path / "data" / "subscribers.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps([
            {"name": "Alice", "webhook_url": "https://hooks.example.com/1", "cities": ["Haifa"]},
            {"name": "Bob", "webhook_url": "https://hooks.example.com/2", "cities": ["Tel Aviv"]},
        ]))

        # Patch the LEGACY_JSON path and create store
        import manager_alert.subscribers as mod
        original_legacy = mod.LEGACY_JSON
        original_default = mod.DEFAULT_DB
        try:
            mod.LEGACY_JSON = json_path
            mod.DEFAULT_DB = tmp_path / "data" / "alerts.db"
            store = SubscriberStore(db_path=mod.DEFAULT_DB)
        finally:
            mod.LEGACY_JSON = original_legacy
            mod.DEFAULT_DB = original_default

        subs = store.list_all()
        assert len(subs) == 2
        assert subs[0].name == "Alice"
        assert subs[1].name == "Bob"
        # JSON file should be renamed
        assert not json_path.exists()
        assert json_path.with_suffix(".json.migrated").exists()
