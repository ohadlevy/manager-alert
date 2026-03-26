"""Manage area subscriptions persisted in a JSON file."""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "subscribers.json"


class SubscriberStore:
    """Thread-safe JSON-backed subscriber store.

    File format:
    {
        "U12345": {"areas": ["תל אביב", "חיפה"], "subscribed_at": "2026-03-26"},
        ...
    }
    """

    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def watch(self, slack_id: str, area: str) -> bool:
        """Add an area to a user's watchlist. Returns True if newly added."""
        data = self._load()
        entry = data.get(slack_id, {"areas": [], "subscribed_at": str(date.today())})
        area = area.strip()
        if area in entry["areas"]:
            return False
        entry["areas"].append(area)
        data[slack_id] = entry
        self._save(data)
        logger.info("User %s now watching: %s", slack_id, area)
        return True

    def unwatch(self, slack_id: str, area: str) -> bool:
        """Remove an area from a user's watchlist. Returns True if removed."""
        data = self._load()
        entry = data.get(slack_id)
        if not entry:
            return False
        area = area.strip()
        if area not in entry["areas"]:
            return False
        entry["areas"].remove(area)
        if not entry["areas"]:
            del data[slack_id]
        else:
            data[slack_id] = entry
        self._save(data)
        logger.info("User %s unwatched: %s", slack_id, area)
        return True

    def list_areas(self, slack_id: str) -> list[str]:
        """Get all areas a user is watching."""
        data = self._load()
        entry = data.get(slack_id, {})
        return list(entry.get("areas", []))

    def get_all_subscribers(self) -> dict[str, list[str]]:
        """Return {slack_id: [areas]} for all subscribers."""
        data = self._load()
        return {uid: entry["areas"] for uid, entry in data.items() if entry["areas"]}
