"""Build plain-text Slack mrkdwn reports from matched alert data."""

from datetime import datetime, timedelta, timezone

from .area_matcher import AreaReport
from .city_names import format_city

ISRAEL_TZ = timezone(timedelta(hours=3))


def _short_types(breakdown: dict[str, int]) -> str:
    """Compact type summary: 'Missiles/UAV' or just 'Missiles'."""
    return "/".join(sorted(breakdown.keys(), key=lambda k: breakdown[k], reverse=True))


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def build_report(
    area_reports: list[AreaReport],
    report_date: datetime | None = None,
    max_areas: int = 20,
) -> str:
    """Build a compact plain-text report for posting via webhook."""
    if report_date is None:
        report_date = datetime.now(ISRAEL_TZ)

    date_str = report_date.strftime("%B %d, %Y")
    lines: list[str] = []

    lines.append(f"*:israel: Israel Daily Vibe Check -- {date_str}*")

    if not area_reports:
        lines.append(":coffee: All quiet! Your Israeli colleagues had a peaceful 24h. Business as usual.")
        return "\n".join(lines)

    total_alerts = sum(r.total_count for r in area_reports)
    total_night = sum(r.night_count for r in area_reports)

    lines.append(f"{_plural(total_alerts, 'siren')} across {_plural(len(area_reports), 'area')} in the last 24h")

    # Night impact — lighthearted but clear
    if total_night > 0:
        night_areas = [r.area_name for r in area_reports if r.night_count > 0]
        night_cities = ", ".join(format_city(a) for a in night_areas[:5])
        extra = f" +{len(night_areas) - 5} more" if len(night_areas) > 5 else ""
        lines.append(
            f":sleepy: *Sleepy colleagues alert!* {_plural(total_night, 'siren')} went off overnight (22:00-07:00) "
            f"in {_plural(len(night_areas), 'area')}. "
            f"Maybe go easy on the morning meetings."
        )

    lines.append("")

    # Compact area list
    shown = area_reports[:max_areas]
    remaining = len(area_reports) - len(shown)

    for r in shown:
        window = r.time_window
        time_str = f"{window[0]}-{window[1]}" if window else ""
        types = _short_types(r.category_breakdown)
        night_marker = " :sleepy:" if r.night_count else ""
        city = format_city(r.area_name)

        lines.append(f"*{city}*  {r.total_count}x {types}  {time_str}{night_marker}")

    if remaining > 0:
        remaining_alerts = sum(r.total_count for r in area_reports[max_areas:])
        lines.append(f"_...and {_plural(remaining, 'more area')} ({_plural(remaining_alerts, 'siren')})_")

    lines.append("")
    lines.append("<https://www.tzevadom.com/|Full alert map> | _Source: Pikud HaOref_")

    return "\n".join(lines)
