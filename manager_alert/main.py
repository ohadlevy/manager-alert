"""Entry point for the Manager Alert daily report system.

Usage:
    python -m manager_alert collect             # Poll oref API, store in SQLite
    python -m manager_alert report              # Send report from stored alerts
    python -m manager_alert report --dry-run    # Preview without sending
    python -m manager_alert report --live       # Fetch live instead of from db
    python -m manager_alert serve               # Run scheduler (collect + daily report)
    python -m manager_alert add-subscriber      # Add a subscriber
    python -m manager_alert update-subscriber   # Update a subscriber
    python -m manager_alert remove-subscriber   # Remove a subscriber
    python -m manager_alert enable-subscriber   # Enable a subscriber
    python -m manager_alert disable-subscriber  # Disable a subscriber
    python -m manager_alert list-subscribers    # List all subscribers
    python -m manager_alert list-cities         # List known city names
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
from .report_builder import build_report, build_subscriber_report
from .slack_client import send_webhook
from .subscribers import Subscriber, SubscriberStore

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


def _send_subscriber_reports(
    area_reports: list[AreaReport],
    report_type: str,
    dry_run: bool = False,
) -> None:
    """Send personalized reports to each enabled subscriber."""
    sub_store = SubscriberStore()
    subscribers = sub_store.get_enabled()
    if not subscribers:
        return

    today = datetime.now(ISRAEL_TZ).date().isoformat()

    for sub in subscribers:
        if not dry_run and sub_store.was_report_sent(sub.id, report_type, today):
            logger.info("Already sent %s report to '%s' today, skipping",
                        report_type, sub.name)
            continue

        sub_text = build_subscriber_report(
            area_reports,
            subscriber_name=sub.name,
            watched_cities=sub.cities,
            report_type=report_type,
        )

        logger.info("Sending %s report to '%s' (cities: %s)",
                     report_type, sub.name, ", ".join(sub.cities))
        logger.debug("Report for '%s':\n%s", sub.name, sub_text)

        if dry_run:
            print(f"\n--- Subscriber: {sub.name} (cities: {', '.join(sub.cities)}) ---")
            send_webhook("", sub_text, dry_run=True)
        else:
            try:
                send_webhook(sub.webhook_url, sub_text)
                sub_store.record_report_sent(sub.id, report_type, today)
                logger.info("Sent %s report to '%s' successfully", report_type, sub.name)
            except Exception:
                logger.exception("Failed to send report to '%s'", sub.name)


def run_report(
    config: dict,
    dry_run: bool = False,
    live: bool = False,
    report_type: str = "daily",
) -> None:
    """Execute a single report cycle.

    report_type: "overnight" (22:00-12:00), "daytime" (12:00-22:00), or "daily" (24h)
    """
    now = datetime.now(ISRAEL_TZ)

    # Determine time window based on report type
    if report_type == "overnight":
        # 22:00 yesterday to 12:00 today
        since = now.replace(hour=22, minute=0, second=0, microsecond=0) - timedelta(days=1)
        until = now.replace(hour=12, minute=0, second=0, microsecond=0)
    elif report_type == "daytime":
        # 12:00 today to 22:00 today
        since = now.replace(hour=12, minute=0, second=0, microsecond=0)
        until = now.replace(hour=22, minute=0, second=0, microsecond=0)
    else:
        since = None
        until = None

    if live:
        logger.info("Fetching alerts live (lookback=%dh)", config["lookback_hours"])
        alerts = fetch_alerts(
            lookback_hours=config["lookback_hours"],
            categories=config["oref_categories"],
            night_start=config["night_start"],
            night_end=config["night_end"],
        )
    else:
        if since and until:
            logger.info("Reading alerts from database (%s, %s-%s)",
                        report_type, since.strftime("%H:%M"), until.strftime("%H:%M"))
            store = AlertStore()
            alerts = store.get_alerts(since=since, until=until)
        else:
            logger.info("Reading alerts from database (lookback=%dh)", config["lookback_hours"])
            store = AlertStore()
            alerts = store.get_alerts(lookback_hours=config["lookback_hours"])

    logger.info("Got %d alerts", len(alerts))

    all_reports = _build_area_reports(alerts)
    report_text = build_report(all_reports, report_type=report_type)

    logger.debug("Broadcast %s report:\n%s", report_type, report_text)

    if dry_run:
        send_webhook("", report_text, dry_run=True)
    else:
        if not config["webhook_url"]:
            logger.error("SLACK_WEBHOOK_URL not set")
            sys.exit(1)
        send_webhook(config["webhook_url"], report_text)

    # Send personalized subscriber reports
    try:
        _send_subscriber_reports(all_reports, report_type, dry_run=dry_run)
    except Exception:
        logger.exception("Subscriber reports failed")

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

    # list-cities
    sub.add_parser("list-cities", help="List all known city names for subscriber config")

    # add-subscriber
    add_sub_p = sub.add_parser("add-subscriber", help="Add a subscriber for personalized alerts")
    add_sub_p.add_argument("--name", required=True, help="Subscriber name (e.g. 'Backend Team')")
    add_sub_p.add_argument("--webhook-url", required=True, help="Slack webhook URL")
    add_sub_p.add_argument("--cities", nargs="+", required=True, help="City names to watch")

    # update-subscriber
    update_sub_p = sub.add_parser("update-subscriber", help="Update a subscriber")
    update_sub_p.add_argument("name", help="Subscriber name to update")
    update_sub_p.add_argument("--webhook-url", help="New Slack webhook URL")
    update_sub_p.add_argument("--cities", nargs="+", help="New city names to watch")

    # remove-subscriber
    remove_sub_p = sub.add_parser("remove-subscriber", help="Remove a subscriber")
    remove_sub_p.add_argument("name", help="Subscriber name to remove")

    # enable-subscriber
    enable_sub_p = sub.add_parser("enable-subscriber", help="Enable a subscriber")
    enable_sub_p.add_argument("name", help="Subscriber name to enable")

    # disable-subscriber
    disable_sub_p = sub.add_parser("disable-subscriber", help="Disable a subscriber")
    disable_sub_p.add_argument("name", help="Subscriber name to disable")

    # list-subscribers
    sub.add_parser("list-subscribers", help="List all subscribers")

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
    elif args.command == "list-cities":
        from .city_names import CITY_REGIONS
        from collections import defaultdict
        by_region: dict[str, list[str]] = defaultdict(list)
        for city, region in sorted(CITY_REGIONS.items()):
            by_region[region].append(city)
        for region in sorted(by_region):
            print(f"\n{region}:")
            print(f"  {', '.join(sorted(by_region[region]))}")
    elif args.command == "add-subscriber":
        from .city_names import CITY_REGIONS
        unknown = [c for c in args.cities if c not in CITY_REGIONS]
        if unknown:
            print(f"Warning: unknown cities (will still be tracked): {', '.join(unknown)}")
            print("Run 'list-cities' to see all known city names.")
        store = SubscriberStore()
        try:
            store.add(name=args.name, webhook_url=args.webhook_url, cities=args.cities)
            print(f"Added subscriber '{args.name}' watching {len(args.cities)} cities.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "update-subscriber":
        if not args.webhook_url and not args.cities:
            print("Error: provide --webhook-url and/or --cities to update", file=sys.stderr)
            sys.exit(1)
        store = SubscriberStore()
        try:
            store.update(name=args.name, webhook_url=args.webhook_url, cities=args.cities)
            print(f"Updated subscriber '{args.name}'.")
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "remove-subscriber":
        store = SubscriberStore()
        try:
            store.remove(name=args.name)
            print(f"Removed subscriber '{args.name}'.")
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "enable-subscriber":
        store = SubscriberStore()
        try:
            store.enable(name=args.name)
            print(f"Enabled subscriber '{args.name}'.")
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "disable-subscriber":
        store = SubscriberStore()
        try:
            store.disable(name=args.name)
            print(f"Disabled subscriber '{args.name}'.")
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "list-subscribers":
        store = SubscriberStore()
        subscribers = store.list_all()
        if not subscribers:
            print("No subscribers configured.")
        else:
            print(f"{'ID':<4} {'Name':<20} {'Cities':<35} {'Enabled':<8} {'Created':<12} {'Sent':>5}")
            print("-" * 84)
            for s in subscribers:
                cities_str = ", ".join(s.cities)
                if len(cities_str) > 33:
                    cities_str = cities_str[:30] + "..."
                created = s.created_at[:10] if s.created_at else ""
                sent = store.get_reports_sent_count(s.id)
                enabled = "yes" if s.enabled else "no"
                print(f"{s.id:<4} {s.name:<20} {cities_str:<35} {enabled:<8} {created:<12} {sent:>5}")


if __name__ == "__main__":
    main()
