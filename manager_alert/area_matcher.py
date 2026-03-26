"""Group Pikud HaOref alert area names by base city.

Handles compound oref names like "Tel Aviv - Center" → "Tel Aviv".
"""

from dataclasses import dataclass, field

from .oref_client import Alert


@dataclass
class AreaReport:
    """Aggregated alert info for a single area."""
    area_name: str
    oref_areas: set[str] = field(default_factory=set)
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


def extract_city_prefix(oref_area: str) -> str:
    """Extract the city prefix from compound oref names.

    "Tel Aviv - Center" → "Tel Aviv"
    "Haifa - Carmel" → "Haifa"
    """
    if " - " in oref_area:
        return oref_area.split(" - ")[0].strip()
    return oref_area
