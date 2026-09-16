from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _base_google_config():
    return {
        "calendar_mode": "google",
        "interval_seconds": 120,
        "min_importance": 2,
        "telegram_bot_token": "token",
        "telegram_chat_id": "chat",
        "trading_economics_api_key": "",
        "google_calendar_id": "primary",
        "google_api_key": "api-key",
        "google_client_id": "",
        "google_client_secret": "",
        "google_refresh_token": "",
        "google_alert_lead_minutes": 30,
        "google_calendar_lookback_minutes": 15,
        "google_calendar_lookahead_minutes": 180,
        "telegram_dry_run": False,
    }


def test_poll_google_sends_alert_for_event_in_window(monkeypatch):
    worker.seen.clear()
    config = _base_google_config()
    start = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    events = [{"id": "test-1", "status": "confirmed", "updated": "2026-01-01T00:00:00Z", "summary": "Test Event", "start": {"dateTime": start}}]
    monkeypatch.setattr(worker, "fetch_google_calendar", lambda _cfg: events)
    monkeypatch.setattr(worker, "send", lambda _text, _cfg: True)

    result = worker.poll_google(config)

    assert result["events_fetched"] == 1
    assert result["alerts_sent"] == 1


def test_poll_google_skips_event_outside_alert_window(monkeypatch):
    worker.seen.clear()
    config = _base_google_config()
    start = (datetime.now(timezone.utc) + timedelta(minutes=120)).isoformat().replace("+00:00", "Z")
    events = [{"id": "test-2", "status": "confirmed", "updated": "2026-01-01T00:00:00Z", "summary": "Far Event", "start": {"dateTime": start}}]
    monkeypatch.setattr(worker, "fetch_google_calendar", lambda _cfg: events)
    monkeypatch.setattr(worker, "send", lambda _text, _cfg: True)

    result = worker.poll_google(config)

    assert result["events_fetched"] == 1
    assert result["alerts_sent"] == 0
    assert result["skipped_outside_alert_window"] == 1


def test_poll_google_deduplicates_same_event(monkeypatch):
    worker.seen.clear()
    config = _base_google_config()
    start = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
    events = [{"id": "test-3", "status": "confirmed", "updated": "2026-01-01T00:00:00Z", "summary": "Duplicate Event", "start": {"dateTime": start}}]
    monkeypatch.setattr(worker, "fetch_google_calendar", lambda _cfg: events)
    monkeypatch.setattr(worker, "send", lambda _text, _cfg: True)

    first = worker.poll_google(config)
    second = worker.poll_google(config)

    assert first["alerts_sent"] == 1
    assert second["alerts_sent"] == 0
    assert second["skipped_seen"] == 1


def test_parse_google_event_start_supports_all_day_date():
    event = {"start": {"date": "2026-12-25"}}
    start = worker.parse_google_event_start(event)

    assert start is not None
    assert start.tzinfo is not None
    assert start.year == 2026
    assert start.month == 12
    assert start.day == 25


def test_poll_google_skips_all_day_events(monkeypatch):
    worker.seen.clear()
    config = _base_google_config()
    events = [{"id": "test-4", "status": "confirmed", "summary": "Holiday", "start": {"date": "2026-12-25"}}]
    monkeypatch.setattr(worker, "fetch_google_calendar", lambda _cfg: events)
    monkeypatch.setattr(worker, "send", lambda _text, _cfg: True)

    result = worker.poll_google(config)

    assert result["alerts_sent"] == 0
    assert result["skipped_all_day"] == 1


def test_fetch_google_calendar_uses_api_key(monkeypatch):
    config = _base_google_config()
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params or {}
        captured["headers"] = headers or {}
        return _FakeResponse({"items": [{"id": "x"}]})

    monkeypatch.setattr(worker.requests, "get", fake_get)

    events = worker.fetch_google_calendar(config)

    assert len(events) == 1
    assert captured["params"]["key"] == "api-key"
    assert "access_token" not in captured["params"]
    assert "Authorization" not in captured["headers"]


def test_fetch_google_calendar_skips_without_api_key_or_oauth(monkeypatch):
    config = _base_google_config()
    config["google_api_key"] = ""
    config["google_client_id"] = ""
    config["google_client_secret"] = ""
    config["google_refresh_token"] = ""

    post_called = {"value": False}

    def fake_post(*_args, **_kwargs):
        post_called["value"] = True
        return _FakeResponse({"access_token": "token"})

    monkeypatch.setattr(worker.requests, "post", fake_post)

    events = worker.fetch_google_calendar(config)

    assert events == []
    assert post_called["value"] is False
