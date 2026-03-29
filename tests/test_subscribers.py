"""Tests for subscribers module."""

import json
from pathlib import Path

from manager_alert.subscribers import Subscriber, add_subscriber, load_subscribers


class TestLoadSubscribers:
    def test_missing_file(self, tmp_path):
        result = load_subscribers(tmp_path / "nonexistent.json")
        assert result == []

    def test_valid_file(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([
            {"name": "Alice", "webhook_url": "https://hooks.example.com/1", "cities": ["Haifa"]},
            {"name": "Bob", "webhook_url": "https://hooks.example.com/2", "cities": ["Tel Aviv", "Herzliya"]},
        ]))
        result = load_subscribers(path)
        assert len(result) == 2
        assert result[0].name == "Alice"
        assert result[0].cities == ["Haifa"]
        assert result[1].cities == ["Tel Aviv", "Herzliya"]

    def test_skips_entry_without_webhook(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([
            {"name": "NoWebhook", "cities": ["Haifa"]},
        ]))
        result = load_subscribers(path)
        assert result == []

    def test_skips_entry_without_cities(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([
            {"name": "NoCities", "webhook_url": "https://hooks.example.com/1"},
        ]))
        result = load_subscribers(path)
        assert result == []

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text("not json")
        result = load_subscribers(path)
        assert result == []

    def test_not_a_list(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps({"name": "oops"}))
        result = load_subscribers(path)
        assert result == []

    def test_empty_list(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([]))
        result = load_subscribers(path)
        assert result == []

    def test_skips_entry_without_name(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([
            {"name": "", "webhook_url": "https://hooks.example.com/1", "cities": ["Haifa"]},
        ]))
        result = load_subscribers(path)
        assert result == []


class TestAddSubscriber:
    def test_creates_new_file(self, tmp_path):
        path = tmp_path / "subs.json"
        add_subscriber("Alice", "https://hooks.example.com/1", ["Haifa"], path=path)
        result = load_subscribers(path)
        assert len(result) == 1
        assert result[0].name == "Alice"
        assert result[0].cities == ["Haifa"]

    def test_appends_to_existing(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text(json.dumps([
            {"name": "Alice", "webhook_url": "https://hooks.example.com/1", "cities": ["Haifa"]},
        ]))
        add_subscriber("Bob", "https://hooks.example.com/2", ["Tel Aviv"], path=path)
        result = load_subscribers(path)
        assert len(result) == 2
        assert result[1].name == "Bob"

    def test_handles_corrupt_file(self, tmp_path):
        path = tmp_path / "subs.json"
        path.write_text("not json")
        add_subscriber("Alice", "https://hooks.example.com/1", ["Haifa"], path=path)
        result = load_subscribers(path)
        assert len(result) == 1
