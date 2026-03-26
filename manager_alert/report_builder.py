"""Build plain-text Slack mrkdwn reports from matched alert data."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .area_matcher import AreaReport
from .city_names import MAJOR_CITIES, get_region, is_known_city

ISRAEL_TZ = timezone(timedelta(hours=3))

# Region display order
REGION_ORDER = [
    "Central Israel",
    "Haifa Area",
    "Northern Israel",
    "Jerusalem Area",
    "Southern Israel",
]


def _plural(n: int, word: str) -> str:
    if word.endswith("y") and not word.endswith("ey"):
        return f"{n} {word[:-1]}ies" if n != 1 else f"{n} {word}"
    return f"{n} {word}{'s' if n != 1 else ''}"


def _severity(total: int, night: int, has_major_cities: bool) -> tuple[str, str]:
    """Return (emoji, label) for the severity line."""
    if night > 0 or (total > 100 and has_major_cities):
        return (":red_circle:", "Heavy")
    if total > 50 or has_major_cities:
        return (":large_orange_circle:", "Elevated")
    return (":large_yellow_circle:", "Moderate")


def build_report(
    area_reports: list[AreaReport],
    report_date: datetime | None = None,
    report_type: str = "daily",
    max_areas: int = 20,
) -> str:
    """Build a compact plain-text report for posting via webhook.

    report_type: "overnight" (22:00-12:00), "daytime" (12:00-22:00), or "daily" (24h)
    """
    if report_date is None:
        report_date = datetime.now(ISRAEL_TZ)

    date_str = report_date.strftime("%B %d, %Y")
    lines: list[str] = []

    titles = {
        "overnight": f"*:israel: Israel Overnight + Morning Update -- {date_str}*",
        "daytime": f"*:israel: Israel Day Summary -- {date_str}*",
        "daily": f"*:israel: Israel Daily Vibe Check -- {date_str}*",
    }
    lines.append(titles.get(report_type, titles["daily"]))

    quiet_messages = {
        "overnight": ":coffee: Quiet night! Your Israeli colleagues slept well. Business as usual.",
        "daytime": ":coffee: Quiet day! No alerts during working hours in Israel.",
        "daily": ":coffee: All quiet! Your Israeli colleagues had a peaceful 24h. Business as usual.",
    }

    if not area_reports:
        lines.append(quiet_messages.get(report_type, quiet_messages["daily"]))
        return "\n".join(lines)

    total_alerts = sum(r.total_count for r in area_reports)
    total_night = sum(r.night_count for r in area_reports)
    hit_cities = {r.area_name for r in area_reports}
    has_major = bool(hit_cities & MAJOR_CITIES)

    # Severity line
    emoji, label = _severity(total_alerts, total_night, has_major)
    severity_detail = f"{_plural(total_alerts, 'siren')}"
    if has_major:
        severity_detail += ", including major cities"
    lines.append(f"{emoji} *{label}* — {severity_detail}")

    # Night alert section (for overnight and daily reports)
    if total_night > 0:
        night_areas = [r for r in area_reports if r.night_count > 0]
        night_cities = [
            f"{r.area_name} {r.night_count}x"
            for r in sorted(night_areas, key=lambda r: r.night_count, reverse=True)[:6]
        ]
        lines.append("")
        lines.append(
            f":sleepy: *Sleepy colleagues alert!* {_plural(total_night, 'siren')} overnight (22:00-07:00)"
        )
        lines.append(f"  {' · '.join(night_cities)}")
        lines.append("  Maybe go easy on the morning meetings.")

    # Explainer
    lines.append("")
    lines.append(":pushpin: _Sirens = take shelter for ~10 min. Most colleagues are safe but disrupted._")
    lines.append("")

    # Group known cities by region
    known_reports = [r for r in area_reports if is_known_city(r.area_name)]
    unknown_reports = [r for r in area_reports if not is_known_city(r.area_name)]

    regions: dict[str, list[AreaReport]] = defaultdict(list)
    for r in known_reports:
        region = get_region(r.area_name) or "Other"
        regions[region].append(r)

    for region in REGION_ORDER:
        if region not in regions:
            continue
        region_areas = sorted(regions[region], key=lambda r: r.total_count, reverse=True)
        city_parts = [
            f"{r.area_name} {r.total_count}x"
            for r in region_areas
        ]
        lines.append(f"*{region}*")
        while city_parts:
            row = city_parts[:4]
            city_parts = city_parts[4:]
            lines.append(f"  {' · '.join(row)}")

    # Summarize unknown/small communities
    unknown_alert_count = sum(r.total_count for r in unknown_reports)
    if unknown_reports:
        lines.append(
            f"\n_...and {_plural(unknown_alert_count, 'siren')} across "
            f"{_plural(len(unknown_reports), 'smaller community')}_"
        )

    lines.append("")
    lines.append("<https://tzevadom.com/|Full alert map> | _Source: Pikud HaOref_")

    return "\n".join(lines)
