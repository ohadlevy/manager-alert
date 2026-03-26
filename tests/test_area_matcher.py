"""Tests for area_matcher module."""

from datetime import datetime, timedelta, timezone

from manager_alert.area_matcher import (
    AreaReport,
    extract_city_prefix,
    normalize,
)
from manager_alert.oref_client import Alert

ISRAEL_TZ = timezone(timedelta(hours=3))


def _make_alert(area: str, hour: int = 12, category: int = 1) -> Alert:
    ts = datetime(2026, 3, 26, hour, 0, tzinfo=ISRAEL_TZ)
    return Alert(
        area=area,
        timestamp=ts,
        category=category,
        category_desc="Missiles",
        is_night=hour >= 22 or hour < 7,
    )


class TestNormalize:
    def test_strips_whitespace(self):
        assert normalize("  תל אביב  ") == "תל אביב"

    def test_collapses_spaces(self):
        assert normalize("תל   אביב") == "תל אביב"

    def test_strips_niqqud(self):
        # תֶּל אָבִיב with niqqud
        assert normalize("תֶּל אָבִיב") == "תל אביב"


class TestExtractCityPrefix:
    def test_compound_name(self):
        assert extract_city_prefix("תל אביב - מרכז העיר") == "תל אביב"

    def test_simple_name(self):
        assert extract_city_prefix("חיפה") == "חיפה"

    def test_multiple_dashes(self):
        assert extract_city_prefix("חיפה - כרמל - מערב") == "חיפה"


class TestAreaReport:
    def test_total_count(self):
        report = AreaReport(area_name="חיפה")
        report.alerts.append(_make_alert("חיפה", 10))
        report.alerts.append(_make_alert("חיפה", 14))
        assert report.total_count == 2

    def test_night_count(self):
        report = AreaReport(area_name="חיפה")
        night = _make_alert("חיפה", 3)
        day = _make_alert("חיפה", 14)
        report.alerts.extend([night, day])
        report.night_alerts.append(night)
        assert report.night_count == 1

    def test_category_breakdown(self):
        report = AreaReport(area_name="חיפה")
        report.alerts.append(_make_alert("חיפה", 10, category=1))
        report.alerts.append(_make_alert("חיפה", 11, category=1))
        uav = Alert(area="חיפה", timestamp=datetime(2026, 3, 26, 12, 0, tzinfo=ISRAEL_TZ),
                     category=2, category_desc="UAV", is_night=False)
        report.alerts.append(uav)
        breakdown = report.category_breakdown
        assert breakdown["Missiles"] == 2
        assert breakdown["UAV"] == 1

    def test_time_window(self):
        report = AreaReport(area_name="חיפה")
        report.alerts.append(_make_alert("חיפה", 10))
        report.alerts.append(_make_alert("חיפה", 14))
        assert report.time_window == ("10:00", "14:00")

    def test_time_window_empty(self):
        report = AreaReport(area_name="חיפה")
        assert report.time_window is None
