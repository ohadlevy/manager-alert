"""Fetch and parse alert data from Pikud HaOref (Israel Home Front Command)."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

ISRAEL_TZ = timezone(timedelta(hours=3))

HISTORY_URL = (
    "https://alerts-history.oref.org.il/Shared/Ajax/GetAlarmsHistory.aspx"
    "?lang=he&mode=1"
)
FALLBACK_URL = (
    "https://www.oref.org.il/warningMessages/alert/History/AlertsHistory.json"
)

CATEGORY_NAMES = {
    1: "Missiles",
    2: "UAV",
    3: "Chemical",
    4: "Warning",
    7: "Earthquake",
    8: "Earthquake",
    9: "Nuclear",
    10: "Terror",
    11: "Tsunami",
    12: "Hazmat",
}

# Hebrew category descriptions returned by the API → short English names
HEBREW_TO_ENGLISH = {
    "ירי רקטות וטילים": "Missiles",
    "חדירת כלי טיס עוין": "UAV",
    "חדירת כלי טיס": "UAV",
    "רעידת אדמה": "Earthquake",
    "חומרים מסוכנים": "Hazmat",
    "אירוע רדיולוגי": "Nuclear",
    "פעולת טרור": "Terror",
    "צונמי": "Tsunami",
    "התגוננות כימית": "Chemical",
}

# Request headers to mimic a browser (oref blocks plain requests)
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


@dataclass
class Alert:
    area: str
    timestamp: datetime
    category: int
    category_desc: str
    is_night: bool


def _parse_history_response(data: list[dict]) -> list[dict]:
    """Parse the extended history endpoint response."""
    results = []
    for item in data:
        try:
            date_str = item.get("alertDate", "")
            if not date_str:
                date_str = f"{item.get('date', '')} {item.get('time', '')}".strip()
            if not date_str:
                continue

            # Try common date formats
            ts = None
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%d.%m.%Y %H:%M:%S",
                "%d.%m.%Y %H:%M",
            ):
                try:
                    ts = datetime.strptime(date_str, fmt).replace(tzinfo=ISRAEL_TZ)
                    break
                except ValueError:
                    continue
            if ts is None:
                # Try ISO format with timezone info
                try:
                    ts = datetime.fromisoformat(date_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=ISRAEL_TZ)
                except ValueError:
                    logger.warning("Could not parse date: %s", date_str)
                    continue

            area = item.get("data", "")
            if isinstance(area, list):
                # Some responses have area as a list
                for a in area:
                    results.append({
                        "area": a.strip(),
                        "timestamp": ts,
                        "category": int(item.get("category", item.get("cat", 0))),
                        "category_desc": item.get(
                            "category_desc",
                            item.get("title", ""),
                        ),
                    })
                continue

            results.append({
                "area": area.strip(),
                "timestamp": ts,
                "category": int(item.get("category", item.get("cat", 0))),
                "category_desc": item.get("category_desc", item.get("title", "")),
            })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Skipping malformed alert record: %s — %s", item, e)
    return results


def _is_night(ts: datetime, night_start: int, night_end: int) -> bool:
    """Check if a timestamp falls within night hours."""
    hour = ts.hour
    if night_start > night_end:
        # Wraps midnight: e.g. 22:00 - 07:00
        return hour >= night_start or hour < night_end
    return night_start <= hour < night_end


def fetch_alerts(
    lookback_hours: int = 24,
    categories: list[int] | None = None,
    night_start: int = 22,
    night_end: int = 7,
) -> list[Alert]:
    """Fetch alerts from the last `lookback_hours` hours.

    Args:
        lookback_hours: How far back to fetch alerts.
        categories: Which alert categories to include (default: [1, 2]).
        night_start: Hour when "night" begins (default: 22).
        night_end: Hour when "night" ends (default: 7).

    Returns:
        List of Alert objects, sorted by timestamp.
    """
    if categories is None:
        categories = [1, 2]

    cutoff = datetime.now(ISRAEL_TZ) - timedelta(hours=lookback_hours)
    raw_alerts = []

    # Try primary endpoint
    try:
        logger.info("Fetching alerts from primary endpoint")
        resp = requests.get(HISTORY_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        # Response may have BOM or be wrapped
        text = resp.text.lstrip("\ufeff")
        data = resp.json() if text else []
        raw_alerts = _parse_history_response(data)
        logger.info("Got %d raw alerts from primary endpoint", len(raw_alerts))
    except (requests.RequestException, ValueError) as e:
        logger.warning("Primary endpoint failed: %s — trying fallback", e)

    # Try fallback if primary failed or returned nothing
    if not raw_alerts:
        try:
            logger.info("Fetching alerts from fallback endpoint")
            resp = requests.get(FALLBACK_URL, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            text = resp.text.lstrip("\ufeff")
            data = resp.json() if text else []
            raw_alerts = _parse_history_response(data)
            logger.info("Got %d raw alerts from fallback endpoint", len(raw_alerts))
        except (requests.RequestException, ValueError) as e:
            logger.error("Fallback endpoint also failed: %s", e)
            return []

    # Filter by time and category
    alerts = []
    for raw in raw_alerts:
        if raw["timestamp"] < cutoff:
            continue
        if raw["category"] not in categories:
            continue
        # Translate Hebrew category to English
        hebrew_desc = raw["category_desc"]
        english_desc = (
            HEBREW_TO_ENGLISH.get(hebrew_desc)
            or CATEGORY_NAMES.get(raw["category"])
            or f"Category {raw['category']}"
        )
        alerts.append(Alert(
            area=raw["area"],
            timestamp=raw["timestamp"],
            category=raw["category"],
            category_desc=english_desc,
            is_night=_is_night(raw["timestamp"], night_start, night_end),
        ))

    alerts.sort(key=lambda a: a.timestamp)
    logger.info(
        "Returning %d alerts after filtering (cutoff=%s, categories=%s)",
        len(alerts), cutoff.isoformat(), categories,
    )
    return alerts
