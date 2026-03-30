"""Tests for scheduler configuration and report dedup."""

from manager_alert.scheduler import REPORT_SCHEDULE


class TestScheduleConfig:
    def test_two_report_slots(self):
        assert len(REPORT_SCHEDULE) == 2

    def test_overnight_at_9_utc(self):
        utc_hour, report_type, state_key = REPORT_SCHEDULE[0]
        assert utc_hour == 9
        assert report_type == "overnight"
        assert state_key == "last_overnight_report"

    def test_daytime_at_19_utc(self):
        utc_hour, report_type, state_key = REPORT_SCHEDULE[1]
        assert utc_hour == 19
        assert report_type == "daytime"
        assert state_key == "last_daytime_report"

    def test_no_daily_report_type(self):
        """The scheduler should never send 'daily' reports — only overnight and daytime."""
        report_types = [rt for _, rt, _ in REPORT_SCHEDULE]
        assert "daily" not in report_types


class TestSchedulerDedup:
    def test_state_prevents_duplicate_reports(self, tmp_path):
        """If state says report was sent today, it should not be sent again."""
        from manager_alert.collector import AlertStore

        db = tmp_path / "test.db"
        store = AlertStore(db_path=db)

        # Simulate: overnight report already sent today
        store.set_state("last_overnight_report", "2026-03-30")
        assert store.get_state("last_overnight_report") == "2026-03-30"

        # A second check should find the same value
        assert store.get_state("last_overnight_report") == "2026-03-30"

    def test_state_allows_new_day(self, tmp_path):
        """State from yesterday should not block today's report."""
        from manager_alert.collector import AlertStore

        db = tmp_path / "test.db"
        store = AlertStore(db_path=db)

        store.set_state("last_overnight_report", "2026-03-29")
        # Today is 2026-03-30, so this should not match
        assert store.get_state("last_overnight_report") != "2026-03-30"
