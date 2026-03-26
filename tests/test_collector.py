"""Tests for collector module."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from manager_alert.collector import AlertStore
from manager_alert.oref_client import Alert

ISRAEL_TZ = timezone(timedelta(hours=3))


def _make_alert(area: str = "חיפה", hour: int = 12, category: int = 1) -> Alert:
    ts = datetime(2026, 3, 26, hour, 0, tzinfo=ISRAEL_TZ)
    return Alert(
        area=area, timestamp=ts, category=category,
        category_desc="Missiles", is_night=hour >= 22 or hour < 7,
    )


class TestAlertStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test.db"
        self.store = AlertStore(self.db_path)

    def test_store_and_retrieve(self):
        alerts = [_make_alert("חיפה", 12), _make_alert("תל אביב", 14)]
        self.store.store(alerts)
        result = self.store.get_alerts(lookback_hours=24)
        assert len(result) == 2

    def test_dedup(self):
        alert = _make_alert("חיפה", 12)
        self.store.store([alert])
        self.store.store([alert])  # same alert again
        assert self.store.count() == 1

    def test_different_alerts_not_deduped(self):
        a1 = _make_alert("חיפה", 12)
        a2 = _make_alert("חיפה", 13)
        self.store.store([a1, a2])
        assert self.store.count() == 2

    def test_prune(self):
        old_alert = Alert(
            area="old", category=1, category_desc="Missiles", is_night=False,
            timestamp=datetime(2026, 3, 20, 12, 0, tzinfo=ISRAEL_TZ),
        )
        new_alert = _make_alert("new", 12)
        self.store.store([old_alert, new_alert])
        assert self.store.count() == 2
        self.store.prune(keep_hours=48)
        assert self.store.count() == 1

    def test_get_alerts_respects_lookback(self):
        old = Alert(
            area="old", category=1, category_desc="Missiles", is_night=False,
            timestamp=datetime(2026, 3, 20, 12, 0, tzinfo=ISRAEL_TZ),
        )
        new = _make_alert("new", 12)
        self.store.store([old, new])
        result = self.store.get_alerts(lookback_hours=24)
        assert len(result) == 1
        assert result[0].area == "new"

    def test_empty_db(self):
        result = self.store.get_alerts(lookback_hours=24)
        assert result == []
        assert self.store.count() == 0
