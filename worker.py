import hashlib
import os
import time
from datetime import datetime, timedelta, timezone

import requests

seen = set()


def configured(v):
    return bool(v and str(v).strip())


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def load_config():
    interval = max(60, env_int("WATCHER_INTERVAL_MINUTES", 5) * 60)
    mode = (os.getenv("CALENDAR_MODE", "trading_economics") or "trading_economics").strip().lower()
    return {
        "calendar_mode": mode,
        "interval_seconds": interval,
        "min_importance": env_int("ECONOMIC_CALENDAR_MIN_IMPORTANCE", 2),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "trading_economics_api_key": os.getenv("TRADING_ECONOMICS_API_KEY", ""),
        "google_calendar_id": os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "google_refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN", ""),
        "google_alert_lead_minutes": env_int("GOOGLE_CALENDAR_ALERT_LEAD_MINUTES", 30),
        "google_calendar_lookback_minutes": env_int("GOOGLE_CALENDAR_LOOKBACK_MINUTES", 15),
        "google_calendar_lookahead_minutes": env_int("GOOGLE_CALENDAR_LOOKAHEAD_MINUTES", 180),
        "telegram_dry_run": (os.getenv("TELEGRAM_DRY_RUN", "0") == "1"),
    }


def send(text, config):
    if config["telegram_dry_run"]:
        print({"telegram_dry_run": True, "message_preview": text[:120]}, flush=True)
        return True
    if not (configured(config["telegram_bot_token"]) and configured(config["telegram_chat_id"])):
        print({"telegram_configured": False, "reason": "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}, flush=True)
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage",
            json={"chat_id": config["telegram_chat_id"], "text": text},
            timeout=15,
        )
        if not r.ok:
            print({"telegram_send_failed": True, "status_code": r.status_code}, flush=True)
        return r.ok
    except Exception as exc:
        print({"telegram_send_error": type(exc).__name__}, flush=True)
        return False


def fetch_trading_economics_calendar(config):
    if not configured(config["trading_economics_api_key"]):
        print({"calendar_fetch_skipped": True, "reason": "missing TRADING_ECONOMICS_API_KEY"}, flush=True)
        return []
    url = "https://api.tradingeconomics.com/calendar/country/united%20states"
    r = requests.get(url, params={"c": config["trading_economics_api_key"]}, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def get_google_access_token(config):
    if not (configured(config["google_client_id"]) and configured(config["google_client_secret"]) and configured(config["google_refresh_token"])):
        return None
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": config["google_client_id"],
            "client_secret": config["google_client_secret"],
            "refresh_token": config["google_refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    token_response.raise_for_status()
    token_data = token_response.json()
    return token_data.get("access_token")


def fetch_google_calendar(config):
    calendar_id = config["google_calendar_id"] or "primary"
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(minutes=max(0, config["google_calendar_lookback_minutes"]))).isoformat()
    time_max = (now + timedelta(minutes=max(1, config["google_calendar_lookahead_minutes"]))).isoformat()

    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeMin": time_min,
        "timeMax": time_max,
    }
    headers = {}
    auth_mode = "none"
    if configured(config["google_api_key"]):
        params["key"] = config["google_api_key"]
        auth_mode = "api_key"
    else:
        access_token = get_google_access_token(config)
        if not configured(access_token):
            print(
                {
                    "calendar_fetch_skipped": True,
                    "reason": "missing GOOGLE_API_KEY or OAuth vars (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN)",
                },
                flush=True,
            )
            return []
        params["access_token"] = access_token
        auth_mode = "oauth_refresh_token"

    url = f"https://www.googleapis.com/calendar/v3/calendars/{requests.utils.quote(calendar_id, safe='')}/events"
    response = requests.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items") if isinstance(payload, dict) else []
    events = items if isinstance(items, list) else []
    print(
        {
            "calendar_mode": "google",
            "google_auth_mode": auth_mode,
            "google_calendar_id": calendar_id,
            "google_events_fetched": len(events),
            "window": {"time_min": time_min, "time_max": time_max},
        },
        flush=True,
    )
    return events


def parse_google_event_start(event):
    start = event.get("start") or {}
    dt = start.get("dateTime")
    day = start.get("date")
    if configured(dt):
        if dt.endswith("Z"):
            dt = dt[:-1] + "+00:00"
        parsed = datetime.fromisoformat(dt)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    if configured(day):
        return datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    return None


def trading_economics_event_id(event):
    raw = "|".join(str(event.get(k, "")) for k in ("Date", "Event", "Actual", "Forecast", "Previous"))
    return hashlib.sha256(raw.encode()).hexdigest()


def google_event_id(event):
    raw = "|".join(str(event.get(k, "")) for k in ("id", "status", "updated"))
    return hashlib.sha256(raw.encode()).hexdigest()


def alert_text_trading_economics(event):
    name = event.get("Event") or event.get("Category") or "US Economic Data"
    actual = event.get("Actual")
    forecast = event.get("Forecast") or event.get("Consensus")
    previous = event.get("Previous")
    return (
        "🚨 MARKET DOST — US DATA\n"
        f"Event: {name}\n"
        f"Actual: {actual}\nForecast: {forecast}\nPrevious: {previous}\n"
        "Silver impact: analysis required from confirmed market reaction.\n"
        "Decision आपका — guaranteed signal नहीं।"
    )


def alert_text_google(event, starts_at):
    name = event.get("summary") or "Calendar Event"
    description = (event.get("description") or "").strip()
    location = (event.get("location") or "").strip()
    lines = [
        "📅 MARKET DOST — CALENDAR ALERT",
        f"Event: {name}",
        f"Start (UTC): {starts_at.isoformat()}",
    ]
    if location:
        lines.append(f"Location: {location}")
    if description:
        lines.append(f"Notes: {description[:200]}")
    lines.append("Silver impact: review around event timing.")
    return "\n".join(lines)


def poll_trading_economics(config):
    alerts = 0
    evaluated = 0
    skipped_low_importance = 0
    skipped_no_actual = 0
    skipped_seen = 0
    events = fetch_trading_economics_calendar(config)
    for event in events:
        evaluated += 1
        importance = int(event.get("Importance") or 0)
        actual = event.get("Actual")
        if importance < config["min_importance"]:
            skipped_low_importance += 1
            continue
        if actual in (None, "", "N/A"):
            skipped_no_actual += 1
            continue
        event_hash = trading_economics_event_id(event)
        if event_hash in seen:
            skipped_seen += 1
            continue
        if send(alert_text_trading_economics(event), config):
            seen.add(event_hash)
            alerts += 1
    return {
        "alerts_sent": alerts,
        "events_fetched": len(events),
        "events_evaluated": evaluated,
        "skipped_low_importance": skipped_low_importance,
        "skipped_no_actual": skipped_no_actual,
        "skipped_seen": skipped_seen,
    }


def poll_google(config):
    alerts = 0
    evaluated = 0
    skipped_cancelled = 0
    skipped_invalid_start = 0
    skipped_outside_alert_window = 0
    skipped_seen = 0

    now = datetime.now(timezone.utc)
    alert_until = now + timedelta(minutes=max(1, config["google_alert_lead_minutes"]))
    alert_from = now - timedelta(minutes=max(0, config["google_calendar_lookback_minutes"]))
    events = fetch_google_calendar(config)
    for event in events:
        evaluated += 1
        status = (event.get("status") or "").lower()
        if status == "cancelled":
            skipped_cancelled += 1
            continue
        start_at = parse_google_event_start(event)
        if not start_at:
            skipped_invalid_start += 1
            continue
        if start_at < alert_from or start_at > alert_until:
            skipped_outside_alert_window += 1
            continue
        event_hash = google_event_id(event)
        if event_hash in seen:
            skipped_seen += 1
            continue
        if send(alert_text_google(event, start_at), config):
            seen.add(event_hash)
            alerts += 1

    return {
        "alerts_sent": alerts,
        "events_fetched": len(events),
        "events_evaluated": evaluated,
        "skipped_cancelled": skipped_cancelled,
        "skipped_invalid_start": skipped_invalid_start,
        "skipped_outside_alert_window": skipped_outside_alert_window,
        "skipped_seen": skipped_seen,
        "alert_window_utc": {"from": alert_from.isoformat(), "to": alert_until.isoformat()},
    }


def poll_once():
    config = load_config()
    mode = config["calendar_mode"]
    print(
        {
            "watcher_cycle_start": True,
            "calendar_mode": mode,
            "telegram_configured": configured(config["telegram_bot_token"]) and configured(config["telegram_chat_id"]),
            "trading_economics_key_configured": configured(config["trading_economics_api_key"]),
            "google_api_key_configured": configured(config["google_api_key"]),
            "google_oauth_configured": configured(config["google_client_id"])
            and configured(config["google_client_secret"])
            and configured(config["google_refresh_token"]),
            "google_calendar_id_configured": configured(config["google_calendar_id"]),
        },
        flush=True,
    )
    try:
        if mode == "google":
            result = poll_google(config)
        else:
            if mode != "trading_economics":
                print({"calendar_mode_unknown": mode, "fallback": "trading_economics"}, flush=True)
            result = poll_trading_economics(config)
        print({"watcher_cycle_result": result, "sleep_seconds": config["interval_seconds"]}, flush=True)
        return result["alerts_sent"], config["interval_seconds"]
    except Exception as exc:
        print({"watcher_error": type(exc).__name__, "calendar_mode": mode}, flush=True)
        return 0, config["interval_seconds"]


if __name__ == "__main__":
    print("Market Dost watcher started", flush=True)
    while True:
        count, sleep_seconds = poll_once()
        print({"alerts_sent": count, "sleep_seconds": sleep_seconds}, flush=True)
        time.sleep(sleep_seconds)
