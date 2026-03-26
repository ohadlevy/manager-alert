"""Send demo reports to Slack to gather feedback on the format."""

import os
import time

from dotenv import load_dotenv

from manager_alert.area_matcher import AreaReport
from manager_alert.oref_client import Alert
from manager_alert.report_builder import build_report
from manager_alert.slack_client import send_webhook

from datetime import datetime, timedelta, timezone

ISRAEL_TZ = timezone(timedelta(hours=3))
DEMO_DATE = datetime(2026, 3, 26, 13, 0, tzinfo=ISRAEL_TZ)


def _alert(area: str, hour: int, cat_desc: str = "Missiles", cat: int = 1) -> Alert:
    return Alert(
        area=area,
        timestamp=datetime(2026, 3, 26, hour, 15, tzinfo=ISRAEL_TZ),
        category=cat, category_desc=cat_desc,
        is_night=hour >= 22 or hour < 7,
    )


def _area(name: str, alerts: list[Alert]) -> AreaReport:
    r = AreaReport(area_name=name)
    for a in alerts:
        r.alerts.append(a)
        r.oref_areas.add(a.area)
        if a.is_night:
            r.night_alerts.append(a)
    return r


def demo_quiet():
    return (
        ":one: *DEMO: Quiet day*\n"
        "───────────────────────\n"
        + build_report([], report_date=DEMO_DATE)
    )


def demo_daytime():
    reports = [
        _area("Tel Aviv", [
            _alert("Tel Aviv - Center", 10),
            _alert("Tel Aviv - Center", 11),
            _alert("Tel Aviv - South", 11, "Hostile aircraft intrusion", 2),
        ]),
        _area("Haifa", [
            _alert("Haifa", 9),
            _alert("Haifa", 10),
        ]),
        _area("Herzliya", [
            _alert("Herzliya", 10),
            _alert("Herzliya", 11),
        ]),
        _area("Nahariya", [
            _alert("Nahariya", 9),
        ]),
        _area("Acre", [
            _alert("Acre", 9),
        ]),
    ]
    return (
        ":two: *DEMO: Daytime alerts only*\n"
        "───────────────────────\n"
        + build_report(reports, report_date=DEMO_DATE)
    )


def demo_night():
    reports = [
        _area("Tel Aviv", [
            _alert("Tel Aviv - Center", 2),
            _alert("Tel Aviv - Center", 3),
            _alert("Tel Aviv - South", 3, "Hostile aircraft intrusion", 2),
            _alert("Tel Aviv - Center", 10),
            _alert("Tel Aviv - South", 11),
        ]),
        _area("Haifa", [
            _alert("Haifa", 1),
            _alert("Haifa", 2),
            _alert("Haifa", 3),
            _alert("Haifa", 14),
        ]),
        _area("Ashdod", [
            _alert("Ashdod", 2),
            _alert("Ashdod", 4),
            _alert("Ashdod", 5),
        ]),
        _area("Herzliya", [
            _alert("Herzliya", 10),
            _alert("Herzliya", 11),
        ]),
        _area("Nahariya", [
            _alert("Nahariya", 3),
            _alert("Nahariya", 9, "Hostile aircraft intrusion", 2),
        ]),
        _area("Ramat Gan", [
            _alert("Ramat Gan", 2),
        ]),
        _area("Acre", [
            _alert("Acre", 9),
        ]),
    ]
    return (
        ":three: *DEMO: Night + daytime alerts (typical rough day)*\n"
        "───────────────────────\n"
        + build_report(reports, report_date=DEMO_DATE)
    )


def demo_today():
    """Use actual live data for a real report demo."""
    from manager_alert.collector import AlertStore
    from manager_alert.area_matcher import extract_city_prefix

    store = AlertStore()
    alerts = store.get_alerts(lookback_hours=24)

    if not alerts:
        from manager_alert.oref_client import fetch_alerts
        alerts = fetch_alerts(lookback_hours=24, categories=[1, 2])

    areas: dict[str, AreaReport] = {}
    for alert in alerts:
        base = extract_city_prefix(alert.area)
        if base not in areas:
            areas[base] = AreaReport(area_name=base)
        areas[base].alerts.append(alert)
        areas[base].oref_areas.add(alert.area)
        if alert.is_night:
            areas[base].night_alerts.append(alert)

    all_reports = sorted(areas.values(), key=lambda r: r.total_count, reverse=True)

    return (
        ":four: *DEMO: Today's actual report*\n"
        "───────────────────────\n"
        + build_report(all_reports, report_date=DEMO_DATE)
    )


if __name__ == "__main__":
    load_dotenv()
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set")
        exit(1)

    intro = (
        "*:mega: Manager Alert — Report Format Demo*\n\n"
        "We're building a daily alert report for managers outside Israel. "
        "Below are sample reports showing different scenarios.\n"
        "Please react with :thumbsup: or :thumbsdown: and share feedback in thread!\n"
        "───────────────────────"
    )

    demos = [intro, demo_quiet(), demo_daytime(), demo_night(), demo_today()]

    for i, text in enumerate(demos):
        print(f"Sending demo {i+1}/{len(demos)}...")
        send_webhook(webhook_url, text)
        if i < len(demos) - 1:
            time.sleep(2)  # avoid rate limiting

    print("All demos sent!")
