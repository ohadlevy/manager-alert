"""Entry point for the Manager Alert daily report system.

Usage:
    python -m manager_alert collect             # Poll oref API, store in SQLite
    python -m manager_alert report              # Send report from stored alerts
    python -m manager_alert report --dry-run    # Preview without sending
    python -m manager_alert report --live       # Fetch live instead of from db
    python -m manager_alert serve               # Run scheduler (collect + daily report)
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from .area_matcher import AreaReport, extract_city_prefix
from .collector import AlertStore, run_collect
from .oref_client import fetch_alerts
from .report_builder import build_report
from .slack_client import send_webhook

logger = logging.getLogger("manager_alert")
ISRAEL_TZ = timezone(timedelta(hours=3))


def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()
    return {
        "webhook_url": os.getenv("SLACK_WEBHOOK_URL", ""),
        "oref_categories": [
            int(c) for c in os.getenv("OREF_CATEGORIES", "1,2").split(",")
        ],
        "lookback_hours": int(os.getenv("ALERT_LOOKBACK_HOURS", "24")),
        "night_start": int(os.getenv("NIGHT_START_HOUR", "22")),
        "night_end": int(os.getenv("NIGHT_END_HOUR", "7")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }


def _build_area_reports(alerts: list) -> list[AreaReport]:
    """Group alerts into AreaReports by base city name."""
    areas: dict[str, AreaReport] = {}
    for alert in alerts:
        base = extract_city_prefix(alert.area)
        if base not in areas:
            areas[base] = AreaReport(area_name=base)
        areas[base].alerts.append(alert)
        areas[base].oref_areas.add(alert.area)
        if alert.is_night:
            areas[base].night_alerts.append(alert)
    return sorted(areas.values(), key=lambda r: r.total_count, reverse=True)


def run_report(config: dict, dry_run: bool = False, live: bool = False) -> None:
    """Execute a single report cycle."""
    if live:
        logger.info("Fetching alerts live (lookback=%dh)", config["lookback_hours"])
        alerts = fetch_alerts(
            lookback_hours=config["lookback_hours"],
            categories=config["oref_categories"],
            night_start=config["night_start"],
            night_end=config["night_end"],
        )
    else:
        logger.info("Reading alerts from database (lookback=%dh)", config["lookback_hours"])
        store = AlertStore()
        alerts = store.get_alerts(lookback_hours=config["lookback_hours"])

    logger.info("Got %d alerts", len(alerts))

    all_reports = _build_area_reports(alerts)
    report_text = build_report(all_reports)

    if dry_run:
        send_webhook("", report_text, dry_run=True)
    else:
        if not config["webhook_url"]:
            logger.error("SLACK_WEBHOOK_URL not set")
            sys.exit(1)
        send_webhook(config["webhook_url"], report_text)

    logger.info("Report cycle complete")


def cmd_collect(config: dict) -> None:
    """Run a single collection cycle."""
    run_collect(
        categories=config["oref_categories"],
        night_start=config["night_start"],
        night_end=config["night_end"],
    )



def main() -> None:
    parser = argparse.ArgumentParser(description="Israel Alert Report for Slack")
    sub = parser.add_subparsers(dest="command")

    # collect
    sub.add_parser("collect", help="Poll oref API and store alerts in SQLite")

    # report
    report_p = sub.add_parser("report", help="Send the daily alert report")
    report_p.add_argument("--dry-run", action="store_true", help="Print report without sending")
    report_p.add_argument("--live", action="store_true", help="Fetch live from API instead of database")

    # serve (replaces cron)
    sub.add_parser("serve", help="Run scheduler: collect every 10min, report daily at 13:00 IST")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config["log_level"]),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.command == "serve":
        from .scheduler import run_loop
        run_loop(config)
    elif args.command == "collect":
        cmd_collect(config)
    elif args.command == "report":
        run_report(config, dry_run=args.dry_run, live=args.live)


if __name__ == "__main__":
    main()
