"""Simple scheduler that replaces cron inside the container.

Runs collect every 10 minutes and report once daily at 13:00 IST.
All output goes to stdout/stderr naturally.
"""

import logging
import signal
import time
from datetime import date, datetime, timedelta, timezone

from .collector import AlertStore

logger = logging.getLogger("manager_alert.scheduler")

ISRAEL_TZ = timezone(timedelta(hours=3))
COLLECT_INTERVAL = 10 * 60  # 10 minutes
REPORT_HOUR = 10  # 10:00 UTC = 13:00 IST
STATE_KEY = "last_report_date"


def run_loop(config: dict) -> None:
    """Run collect every 10 min, report daily at REPORT_HOUR UTC."""
    from .main import cmd_collect, run_report

    store = AlertStore()
    stop = False

    def _handle_signal(signum, frame):
        nonlocal stop
        logger.info("Received signal %d, shutting down...", signum)
        stop = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_collect = 0.0

    # Read last report date from DB
    saved = store.get_state(STATE_KEY)
    last_report_date = date.fromisoformat(saved) if saved else None

    logger.info("Scheduler started (collect every 10min, report daily at 13:00 IST)")
    if last_report_date:
        logger.info("Last report was sent on %s", last_report_date)

    # Initial collect on startup
    try:
        logger.info("Initial collection...")
        cmd_collect(config)
        last_collect = time.monotonic()
    except Exception:
        logger.exception("Initial collect failed")

    while not stop:
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        # Collect every 10 minutes
        if time.monotonic() - last_collect >= COLLECT_INTERVAL:
            try:
                logger.info("Collecting alerts...")
                cmd_collect(config)
            except Exception:
                logger.exception("Collect failed")
            last_collect = time.monotonic()

        # Report once daily at REPORT_HOUR UTC
        if now_utc.hour >= REPORT_HOUR and last_report_date != today:
            try:
                logger.info("Sending daily report...")
                run_report(config)
                last_report_date = today
                store.set_state(STATE_KEY, today.isoformat())
            except Exception:
                logger.exception("Report failed")

        time.sleep(30)

    logger.info("Scheduler stopped")
