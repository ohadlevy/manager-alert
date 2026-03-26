"""Tests for slack_client module."""

from unittest.mock import patch, Mock

from manager_alert.slack_client import send_webhook


class TestSendWebhook:
    def test_dry_run_returns_true(self, capsys):
        result = send_webhook("", "test report", dry_run=True)
        assert result is True
        captured = capsys.readouterr()
        assert "test report" in captured.out

    @patch("manager_alert.slack_client.requests.post")
    def test_successful_post(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()
        result = send_webhook("https://example.com/webhook", "report text")
        assert result is True
        mock_post.assert_called_once_with(
            "https://example.com/webhook",
            json={"report": "report text"},
            timeout=10,
        )

    @patch("manager_alert.slack_client.requests.post")
    def test_failed_post(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("connection error")
        result = send_webhook("https://example.com/webhook", "report text")
        assert result is False
