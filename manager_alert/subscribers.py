"""Load and manage subscriber configurations for personalized alert reports."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SUBSCRIBERS_FILE = Path(__file__).resolve().parent.parent / "data" / "subscribers.json"


@dataclass
class Subscriber:
    """A subscriber who receives filtered reports for specific cities."""
    name: str
    webhook_url: str
    cities: list[str] = field(default_factory=list)


def load_subscribers(path: Path | str = DEFAULT_SUBSCRIBERS_FILE) -> list[Subscriber]:
    """Load subscribers from a JSON file.

    Returns an empty list if the file doesn't exist or is invalid.
    """
    path = Path(path)
    if not path.exists():
        logger.debug("No subscribers file at %s", path)
        return []

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load subscribers from %s: %s", path, e)
        return []

    if not isinstance(data, list):
        logger.error("Subscribers file must contain a JSON array")
        return []

    subscribers = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        webhook_url = entry.get("webhook_url", "")
        cities = entry.get("cities", [])
        if not name or not webhook_url or not cities:
            logger.warning("Skipping subscriber %r: missing name, webhook_url, or cities", name)
            continue
        subscribers.append(Subscriber(name=name, webhook_url=webhook_url, cities=cities))

    logger.info("Loaded %d subscriber(s)", len(subscribers))
    return subscribers
