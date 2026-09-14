import os, time, hashlib, requests

TE_KEY = os.getenv("TRADING_ECONOMICS_API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
INTERVAL = max(60, int(os.getenv("WATCHER_INTERVAL_MINUTES", "5")) * 60)
MIN_IMPORTANCE = int(os.getenv("ECONOMIC_CALENDAR_MIN_IMPORTANCE", "2"))
seen = set()


def configured(v):
    return bool(v and v.strip())


def send(text):
    if not (configured(TG_TOKEN) and configured(TG_CHAT)):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text}, timeout=15)
        return r.ok
    except Exception:
        return False


def fetch_calendar():
    if not configured(TE_KEY):
        return []
    url = "https://api.tradingeconomics.com/calendar/country/united%20states"
    r = requests.get(url, params={"c": TE_KEY}, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def event_id(e):
    raw = "|".join(str(e.get(k, "")) for k in ("Date", "Event", "Actual", "Forecast", "Previous"))
    return hashlib.sha256(raw.encode()).hexdigest()


def alert_text(e):
    event = e.get("Event") or e.get("Category") or "US Economic Data"
    actual = e.get("Actual")
    forecast = e.get("Forecast") or e.get("Consensus")
    previous = e.get("Previous")
    return (
        "🚨 MARKET DOST — US DATA\n"
        f"Event: {event}\n"
        f"Actual: {actual}\nForecast: {forecast}\nPrevious: {previous}\n"
        "Silver impact: analysis required from confirmed market reaction.\n"
        "Decision आपका — guaranteed signal नहीं।"
    )


def poll_once():
    alerts = 0
    try:
        for e in fetch_calendar():
            importance = int(e.get("Importance") or 0)
            actual = e.get("Actual")
            if importance < MIN_IMPORTANCE or actual in (None, "", "N/A"):
                continue
            eid = event_id(e)
            if eid in seen:
                continue
            if send(alert_text(e)):
                seen.add(eid)
                alerts += 1
    except Exception as exc:
        print({"watcher_error": type(exc).__name__}, flush=True)
    return alerts


if __name__ == "__main__":
    print("Market Dost watcher started", flush=True)
    while True:
        count = poll_once()
        print({"alerts_sent": count, "sleep_seconds": INTERVAL}, flush=True)
        time.sleep(INTERVAL)
