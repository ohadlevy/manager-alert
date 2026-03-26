"""Send reports to Slack via Workflow Builder webhook."""

import logging

import requests

logger = logging.getLogger(__name__)


def send_webhook(webhook_url: str, report_text: str, dry_run: bool = False) -> bool:
    """Post report text to a Slack Workflow Builder webhook.

    Args:
        webhook_url: The webhook URL from Workflow Builder.
        report_text: The formatted report string.
        dry_run: If True, print instead of sending.

    Returns:
        True if sent successfully (or dry run), False on error.
    """
    if dry_run:
        print("\n=== REPORT (dry run) ===")
        print(report_text)
        print("========================\n")
        return True

    try:
        resp = requests.post(
            webhook_url,
            json={"report": report_text},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Posted report to webhook successfully")
        return True
    except requests.RequestException as e:
        logger.error("Failed to post to webhook: %s", e)
        return False
