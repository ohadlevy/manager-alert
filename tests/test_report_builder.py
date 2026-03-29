"""Tests for report_builder module."""

from datetime import datetime, timedelta, timezone

from manager_alert.area_matcher import AreaReport
from manager_alert.oref_client import Alert
from manager_alert.report_builder import build_report, build_subscriber_report

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
        reports = [_make_area_report("Tel Aviv", [2, 3, 14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Tel Aviv" in text
        assert "3x" in text

    def test_night_banner(self):
        reports = [_make_area_report("Haifa", [2, 3])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Sleepy" in text
        assert "morning meetings" in text

    def test_no_night_for_day_alerts(self):
        reports = [_make_area_report("Haifa", [10, 14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Sleepy" not in text

    def test_tzevadom_link(self):
        reports = [_make_area_report("Haifa", [14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "tzevadom.com" in text

    def test_unknown_city_in_summary(self):
        reports = [_make_area_report("Some Village", [14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "smaller communit" in text

    def test_remaining_areas(self):
        reports = [_make_area_report(f"area{i}", [12]) for i in range(25)]
        text = build_report(reports, report_date=TEST_DATE)
        assert "smaller communit" in text

    def test_severity_heavy(self):
        reports = [_make_area_report("Tel Aviv", [2, 3])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Heavy" in text

    def test_severity_elevated(self):
        reports = [_make_area_report("Tel Aviv", [10, 14])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Elevated" in text

    def test_severity_moderate(self):
        reports = [_make_area_report("Some Village", [10])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Moderate" in text

    def test_region_grouping(self):
        reports = [
            _make_area_report("Tel Aviv", [10]),
            _make_area_report("Haifa", [10]),
        ]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Central Israel" in text
        assert "Haifa Area" in text

    def test_explainer_line(self):
        reports = [_make_area_report("Tel Aviv", [10])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "take shelter" in text

    def test_raanana_is_major(self):
        reports = [_make_area_report("Ra'anana", [10])]
        text = build_report(reports, report_date=TEST_DATE)
        assert "Elevated" in text
        assert "Ra'anana" in text


class TestBuildSubscriberReport:
    def test_filters_to_watched_cities(self):
        reports = [
            _make_area_report("Tel Aviv", [10, 14]),
            _make_area_report("Haifa", [10]),
            _make_area_report("Sderot", [10]),
        ]
        text = build_subscriber_report(
            reports, subscriber_name="Ziv",
            watched_cities=["Tel Aviv", "Haifa"], report_date=TEST_DATE,
        )
        assert text is not None
        assert "Tel Aviv" in text
        assert "Haifa" in text
        assert "Sderot" not in text
        assert "Ziv" in text

    def test_returns_none_when_no_matching_cities(self):
        reports = [_make_area_report("Sderot", [10])]
        text = build_subscriber_report(
            reports, subscriber_name="Ziv",
            watched_cities=["Tel Aviv"], report_date=TEST_DATE,
        )
        assert text is None

    def test_case_insensitive_matching(self):
        reports = [_make_area_report("Tel Aviv", [10])]
        text = build_subscriber_report(
            reports, subscriber_name="Ziv",
            watched_cities=["tel aviv"], report_date=TEST_DATE,
        )
        assert text is not None
        assert "Tel Aviv" in text

    def test_night_alerts_shown(self):
        reports = [_make_area_report("Haifa", [2, 3])]
        text = build_subscriber_report(
            reports, subscriber_name="Ziv",
            watched_cities=["Haifa"], report_date=TEST_DATE,
        )
        assert text is not None
        assert "overnight" in text
        assert "Haifa" in text

    def test_report_type_in_title(self):
        reports = [_make_area_report("Tel Aviv", [10])]
        text = build_subscriber_report(
            reports, subscriber_name="Ziv",
            watched_cities=["Tel Aviv"], report_date=TEST_DATE,
            report_type="overnight",
        )
        assert "Overnight" in text

    def test_empty_area_reports(self):
        text = build_subscriber_report(
            [], subscriber_name="Ziv",
            watched_cities=["Tel Aviv"], report_date=TEST_DATE,
        )
        assert text is None
