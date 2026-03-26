"""Tests for report_builder module."""

from datetime import datetime, timedelta, timezone

from manager_alert.area_matcher import AreaReport
from manager_alert.oref_client import Alert
from manager_alert.report_builder import build_report

ISRAEL_TZ = timezone(timedelta(hours=3))
TEST_DATE = datetime(2026, 3, 26, 13, 0, tzinfo=ISRAEL_TZ)


def _make_alert(area: str, hour: int = 12, category_desc: str = "Missiles") -> Alert:
    ts = datetime(2026, 3, 26, hour, 0, tzinfo=ISRAEL_TZ)
    return Alert(
        area=area, timestamp=ts, category=1, category_desc=category_desc,
        is_night=hour >= 22 or hour < 7,
    )


def _make_area_report(area: str, hours: list[int]) -> AreaReport:
    report = AreaReport(area_name=area)
    for h in hours:
        alert = _make_alert(area, hour=h)
        report.alerts.append(alert)
        report.oref_areas.add(area)
        if alert.is_night:
            report.night_alerts.append(alert)
    return report


class TestBuildReport:
    def test_quiet_day(self):
        text = build_report([], report_date=TEST_DATE)
        assert "quiet" in text.lower() or "peaceful" in text.lower()

    def test_with_alerts(self):
        reports = [_make_area_report("תל אביב", [2, 3, 14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Tel Aviv" in text
        assert "3x" in text

    def test_night_banner(self):
        reports = [_make_area_report("חיפה", [2, 3])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Sleepy" in text
        assert "morning meetings" in text

    def test_no_night_for_day_alerts(self):
        reports = [_make_area_report("חיפה", [10, 14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Sleepy" not in text

    def test_english_city_names(self):
        reports = [_make_area_report("חיפה", [14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Haifa" in text

    def test_unknown_city_stays_hebrew(self):
        reports = [_make_area_report("כפר קאסם", [14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "כפר קאסם" in text

    def test_tzevadom_link(self):
        reports = [_make_area_report("חיפה", [14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "tzevadom.com" in text

    def test_remaining_areas(self):
        reports = [_make_area_report(f"area{i}", [12]) for i in range(25)]
        text = build_report(reports, report_date=TEST_DATE, max_areas=20)
        assert "5 more areas" in text
