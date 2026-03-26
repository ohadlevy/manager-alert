"""Match Pikud HaOref alert area names to subscriber-watched cities.

Three-tier matching:
1. Exact match after normalization (strip niqqud, NFC, whitespace).
2. Prefix match: oref "תל אביב - מרכז העיר" matches subscriber "תל אביב".
3. Fuzzy match via rapidfuzz as a last resort.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .oref_client import Alert

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85


@dataclass
class AreaReport:
    """Aggregated alert info for a single matched area."""
    area_name: str  # The subscriber's watched city name
    oref_areas: set[str] = field(default_factory=set)  # Original oref area names matched
    alerts: list[Alert] = field(default_factory=list)
    night_alerts: list[Alert] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.alerts)

    @property
    def night_count(self) -> int:
        return len(self.night_alerts)

    @property
    def category_breakdown(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.alerts:
            counts[a.category_desc] = counts.get(a.category_desc, 0) + 1
        return counts

    @property
    def time_window(self) -> tuple[str, str] | None:
        if not self.alerts:
            return None
        times = sorted(a.timestamp for a in self.alerts)
        return (times[0].strftime("%H:%M"), times[-1].strftime("%H:%M"))


def normalize(name: str) -> str:
    """Normalize a Hebrew area name for matching."""
    # Remove Hebrew niqqud (diacritics) U+0591 to U+05C7
    name = re.sub(r"[\u0591-\u05C7]", "", name)
    # NFC normalize
    name = unicodedata.normalize("NFC", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def extract_city_prefix(oref_area: str) -> str:
    """Extract the city prefix from compound oref names.

    "תל אביב - מרכז העיר" → "תל אביב"
    "חיפה - כרמל ועיר תחתית" → "חיפה"
    """
    if " - " in oref_area:
        return oref_area.split(" - ")[0].strip()
    return oref_area


def _match_area(oref_area: str, watched_areas: list[str]) -> str | None:
    """Try to match an oref area name to one of the watched areas.

    Returns the matching watched area name, or None.
    """
    norm_oref = normalize(oref_area)
    prefix = normalize(extract_city_prefix(oref_area))

    for watched in watched_areas:
        norm_watched = normalize(watched)

        # Tier 1: exact match
        if norm_oref == norm_watched:
            return watched

        # Tier 2: prefix match (oref is more specific than watched)
        if prefix == norm_watched:
            return watched

        # Tier 2b: watched is more specific than oref
        watched_prefix = normalize(extract_city_prefix(watched))
        if watched_prefix == norm_oref:
            return watched

    # Tier 3: fuzzy match
    best_score = 0
    best_match = None
    for watched in watched_areas:
        norm_watched = normalize(watched)
        score = fuzz.ratio(prefix, norm_watched)
        if score > best_score:
            best_score = score
            best_match = watched

    if best_match and best_score >= FUZZY_THRESHOLD:
        logger.warning(
            "Fuzzy matched oref area '%s' to watched area '%s' (score=%d)",
            oref_area, best_match, best_score,
        )
        return best_match

    return None


def match_alerts_to_subscribers(
    alerts: list[Alert],
    subscribers: dict[str, list[str]],
) -> dict[str, list[AreaReport]]:
    """Match alerts to subscriber watchlists.

    Args:
        alerts: List of alerts from oref_client.
        subscribers: {slack_id: [watched_area_names]}.

    Returns:
        {slack_id: [AreaReport]} — one AreaReport per matched watched area.
    """
    # Build a global set of all watched areas across all subscribers
    all_watched: set[str] = set()
    for areas in subscribers.values():
        all_watched.update(areas)

    # Pre-match each unique oref area to watched areas
    oref_to_watched: dict[str, str | None] = {}
    for alert in alerts:
        if alert.area not in oref_to_watched:
            oref_to_watched[alert.area] = _match_area(alert.area, list(all_watched))

    # Build per-subscriber reports
    result: dict[str, list[AreaReport]] = {}

    for slack_id, watched_areas in subscribers.items():
        area_reports: dict[str, AreaReport] = {}

        for alert in alerts:
            matched_watched = oref_to_watched.get(alert.area)
            if matched_watched is None or matched_watched not in watched_areas:
                continue

            if matched_watched not in area_reports:
                area_reports[matched_watched] = AreaReport(area_name=matched_watched)

            report = area_reports[matched_watched]
            report.oref_areas.add(alert.area)
            report.alerts.append(alert)
            if alert.is_night:
                report.night_alerts.append(alert)

        if area_reports:
            # Sort by alert count descending
            result[slack_id] = sorted(
                area_reports.values(),
                key=lambda r: r.total_count,
                reverse=True,
            )

    return result
