"""Simple scheduler that replaces cron inside the container.

Runs collect every 10 minutes and sends two reports daily:
  - 12:00 IST (09:00 UTC): overnight + morning report (22:00-12:00)
  - 22:00 IST (19:00 UTC): daytime report (12:00-22:00)

All output goes to stdout/stderr naturally.
"""

import logging
import signal
import time
from datetime import datetime, timedelta, timezone

from .collector import AlertStore

logger = logging.getLogger("manager_alert.scheduler")

ISRAEL_TZ = timezone(timedelta(hours=3))
COLLECT_INTERVAL = 10 * 60  # 10 minutes

# Report schedule: (UTC hour, report_type, state_key)
REPORT_SCHEDULE = [
    (9, "overnight", "last_overnight_report"),   # 09:00 UTC = 12:00 IST
    (19, "daytime", "last_daytime_report"),       # 19:00 UTC = 22:00 IST
]


def run_loop(config: dict) -> None:
    """Run collect every 10 min, reports at scheduled times."""
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

    # Read last report dates from DB
    last_sent: dict[str, str | None] = {}
    for _, _, key in REPORT_SCHEDULE:
        last_sent[key] = store.get_state(key)

    logger.info("Scheduler started (collect every 10min, reports at 12:00 and 22:00 IST)")
    for _, rtype, key in REPORT_SCHEDULE:
        if last_sent[key]:
            logger.info("Last %s report: %s", rtype, last_sent[key])

    # Initial collect on startup
    try:
        logger.info("Initial collection...")
        cmd_collect(config)
        last_collect = time.monotonic()
    except Exception:
        logger.exception("Initial collect failed")

    while not stop:
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date().isoformat()

        # Collect every 10 minutes
        if time.monotonic() - last_collect >= COLLECT_INTERVAL:
            try:
                logger.info("Collecting alerts...")
                cmd_collect(config)
            except Exception:
                logger.exception("Collect failed")
            last_collect = time.monotonic()

        # Check each scheduled report
        for utc_hour, report_type, state_key in REPORT_SCHEDULE:
            if now_utc.hour >= utc_hour:
                if last_sent[state_key] == today:
                    continue
                # Double-check DB state in case it was updated by another process
                db_state = store.get_state(state_key)
                if db_state == today:
                    logger.info("Skipping %s report — already sent today (db=%s)",
                                report_type, db_state)
                    last_sent[state_key] = today
                    continue
                try:
                    logger.info("Triggering %s report (utc_hour=%d, last_sent=%s)",
                                report_type, utc_hour, last_sent[state_key])
                    run_report(config, report_type=report_type)
                    last_sent[state_key] = today
                    store.set_state(state_key, today)
                    logger.info("Completed %s report, state saved for %s",
                                report_type, today)
                except Exception:
                    logger.exception("%s report failed", report_type)

        time.sleep(30)

    logger.info("Scheduler stopped")
