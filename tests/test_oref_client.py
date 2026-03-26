"""Tests for oref_client module."""

from datetime import datetime, timedelta, timezone

from manager_alert.oref_client import Alert, _is_night, _parse_history_response

ISRAEL_TZ = timezone(timedelta(hours=3))


class TestIsNight:
    def test_midnight_is_night(self):
        ts = datetime(2026, 3, 26, 0, 30, tzinfo=ISRAEL_TZ)
        assert _is_night(ts, 22, 7)

    def test_3am_is_night(self):
        ts = datetime(2026, 3, 26, 3, 0, tzinfo=ISRAEL_TZ)
        assert _is_night(ts, 22, 7)

    def test_6am_is_night(self):
        ts = datetime(2026, 3, 26, 6, 45, tzinfo=ISRAEL_TZ)
        assert _is_night(ts, 22, 7)

    def test_7am_is_not_night(self):
        ts = datetime(2026, 3, 26, 7, 0, tzinfo=ISRAEL_TZ)
        assert not _is_night(ts, 22, 7)

    def test_noon_is_not_night(self):
        ts = datetime(2026, 3, 26, 12, 0, tzinfo=ISRAEL_TZ)
        assert not _is_night(ts, 22, 7)

    def test_22_is_night(self):
        ts = datetime(2026, 3, 26, 22, 0, tzinfo=ISRAEL_TZ)
        assert _is_night(ts, 22, 7)

    def test_2130_is_not_night(self):
        ts = datetime(2026, 3, 26, 21, 30, tzinfo=ISRAEL_TZ)
        assert not _is_night(ts, 22, 7)


class TestParseHistoryResponse:
    def test_standard_format(self):
        data = [
            {
                "alertDate": "2026-03-26 02:15:00",
                "title": "Missiles",
                "data": "Tel Aviv - Center",
                "category": 1,
            }
        ]
        result = _parse_history_response(data)
        assert len(result) == 1
        assert result[0]["area"] == "Tel Aviv - Center"
        assert result[0]["category"] == 1

    def test_list_data_field(self):
        data = [
            {
                "alertDate": "2026-03-26 02:15:00",
                "title": "Missiles",
                "data": ["Tel Aviv", "Ramat Gan"],
                "category": 1,
            }
        ]
        result = _parse_history_response(data)
        assert len(result) == 2
        assert result[0]["area"] == "Tel Aviv"
        assert result[1]["area"] == "Ramat Gan"

    def test_missing_date_skipped(self):
        data = [{"title": "test", "data": "somewhere", "category": 1}]
        result = _parse_history_response(data)
        assert len(result) == 0

    def test_malformed_record_skipped(self):
        data = [{"garbage": True}]
        result = _parse_history_response(data)
        assert len(result) == 0

    def test_dot_date_format(self):
        data = [
            {
                "alertDate": "26.03.2026 02:15:00",
                "title": "Missiles",
                "data": "Haifa",
                "category": 1,
            }
        ]
        result = _parse_history_response(data)
        assert len(result) == 1
        assert result[0]["area"] == "Haifa"
