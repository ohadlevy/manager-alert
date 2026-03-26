"""Tests for area_matcher module."""

from datetime import datetime, timedelta, timezone

from manager_alert.area_matcher import AreaReport, extract_city_prefix
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


class TestExtractCityPrefix:
    def test_compound_name(self):
        assert extract_city_prefix("Tel Aviv - Center") == "Tel Aviv"

    def test_simple_name(self):
        assert extract_city_prefix("Haifa") == "Haifa"

    def test_multiple_dashes(self):
        assert extract_city_prefix("Haifa - Carmel - West") == "Haifa"


class TestAreaReport:
    def test_total_count(self):
        report = AreaReport(area_name="Haifa")
        report.alerts.append(_make_alert("Haifa", 10))
        report.alerts.append(_make_alert("Haifa", 14))
        assert report.total_count == 2

    def test_night_count(self):
        report = AreaReport(area_name="Haifa")
        night = _make_alert("Haifa", 3)
        day = _make_alert("Haifa", 14)
        report.alerts.extend([night, day])
        report.night_alerts.append(night)
        assert report.night_count == 1

    def test_category_breakdown(self):
        report = AreaReport(area_name="Haifa")
        report.alerts.append(_make_alert("Haifa", 10, category=1))
        report.alerts.append(_make_alert("Haifa", 11, category=1))
        uav = Alert(area="Haifa", timestamp=datetime(2026, 3, 26, 12, 0, tzinfo=ISRAEL_TZ),
                     category=2, category_desc="UAV", is_night=False)
        report.alerts.append(uav)
        breakdown = report.category_breakdown
        assert breakdown["Missiles"] == 2
        assert breakdown["UAV"] == 1

    def test_time_window(self):
        report = AreaReport(area_name="Haifa")
        report.alerts.append(_make_alert("Haifa", 10))
        report.alerts.append(_make_alert("Haifa", 14))
        assert report.time_window == ("10:00", "14:00")

    def test_time_window_empty(self):
        report = AreaReport(area_name="Haifa")
        assert report.time_window is None
