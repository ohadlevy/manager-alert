"""Tests for area_matcher module."""

from datetime import datetime, timedelta, timezone

from manager_alert.area_matcher import (
    AreaReport,
    extract_city_prefix,
    match_alerts_to_subscribers,
    normalize,
    _match_area,
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


class TestMatchArea:
    def test_exact_match(self):
        assert _match_area("אשדוד", ["אשדוד", "חיפה"]) == "אשדוד"

    def test_prefix_match(self):
        assert _match_area("תל אביב - מרכז העיר", ["תל אביב", "חיפה"]) == "תל אביב"

    def test_no_match(self):
        assert _match_area("קריית שמונה", ["אשדוד", "חיפה"]) is None

    def test_reverse_prefix(self):
        # Subscriber wrote more specific name than oref
        assert _match_area("חיפה", ["חיפה - כרמל", "אשדוד"]) == "חיפה - כרמל"


class TestMatchAlertsToSubscribers:
    def test_basic_matching(self):
        alerts = [
            _make_alert("תל אביב - מרכז העיר"),
            _make_alert("חיפה"),
        ]
        subscribers = {
            "U1": ["תל אביב"],
            "U2": ["חיפה", "אשדוד"],
        }
        result = match_alerts_to_subscribers(alerts, subscribers)

        assert "U1" in result
        assert len(result["U1"]) == 1
        assert result["U1"][0].area_name == "תל אביב"

        assert "U2" in result
        assert len(result["U2"]) == 1
        assert result["U2"][0].area_name == "חיפה"

    def test_no_matching_alerts(self):
        alerts = [_make_alert("קריית שמונה")]
        subscribers = {"U1": ["אשדוד"]}
        result = match_alerts_to_subscribers(alerts, subscribers)
        assert "U1" not in result

    def test_night_alerts_tracked(self):
        alerts = [
            _make_alert("חיפה", hour=3),  # night
            _make_alert("חיפה", hour=14),  # day
        ]
        subscribers = {"U1": ["חיפה"]}
        result = match_alerts_to_subscribers(alerts, subscribers)

        report = result["U1"][0]
        assert report.total_count == 2
        assert report.night_count == 1

    def test_multiple_subscribers_same_area(self):
        alerts = [_make_alert("תל אביב")]
        subscribers = {
            "U1": ["תל אביב"],
            "U2": ["תל אביב"],
        }
        result = match_alerts_to_subscribers(alerts, subscribers)
        assert "U1" in result
        assert "U2" in result

    def test_category_breakdown(self):
        alerts = [
            _make_alert("חיפה", category=1),
            _make_alert("חיפה", category=1),
            _make_alert("חיפה", category=2),
        ]
        alerts[2] = Alert(
            area="חיפה",
            timestamp=alerts[2].timestamp,
            category=2,
            category_desc="UAV Intrusion",
            is_night=False,
        )
        subscribers = {"U1": ["חיפה"]}
        result = match_alerts_to_subscribers(alerts, subscribers)
        breakdown = result["U1"][0].category_breakdown
        assert breakdown["Missiles"] == 2
        assert breakdown["UAV Intrusion"] == 1
