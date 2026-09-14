import os, time, requests
from fastapi import FastAPI, Request

app = FastAPI(title="Market Dost AI", version="2.0.0")

SILVER_KG = float(os.getenv("SILVER_KG", "28"))
AVG_COST = float(os.getenv("SILVER_AVG_COST_INR_PER_KG", "171000"))
TZ = os.getenv("TIMEZONE", "Asia/Kolkata")
TD_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TE_KEY = os.getenv("TRADING_ECONOMICS_API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")


def configured(v: str) -> bool:
    return bool(v and v.strip())


def td_price(symbol: str):
    if not configured(TD_KEY):
        return None
    r = requests.get("https://api.twelvedata.com/price", params={"symbol": symbol, "apikey": TD_KEY}, timeout=12)
    r.raise_for_status()
    data = r.json()
    if "price" not in data:
        return None
    return float(data["price"])


def telegram_send(text: str):
    if not (configured(TG_TOKEN) and configured(TG_CHAT)):
        return {"sent": False, "reason": "telegram_not_configured"}
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text}, timeout=12)
    return {"sent": r.ok, "status": r.status_code}


def parity_inr_kg(xag_usd: float, usdinr: float):
    return xag_usd * usdinr * 32.1507466


def score_from_change(xag=None, dxy=None, y10=None):
    score = 50
    reasons = []
    if xag is not None:
        reasons.append("live silver feed available")
    if dxy is not None:
        reasons.append("dollar factor available")
    if y10 is not None:
        reasons.append("yield factor available")
    confidence = "LOW" if len(reasons) < 2 else "MEDIUM"
    return {"score": score, "bias": "Neutral", "confidence": confidence, "reasons": reasons}


@app.get("/")
def root():
    return {"name": "Market Dost AI", "version": "2.0.0", "status": "running"}


@app.get("/health/live")
def health_live():
    return {"ok": True, "service": "market-dost-api"}


@app.get("/health/ready")
def health_ready():
    missing = []
    if not configured(TD_KEY): missing.append("TWELVE_DATA_API_KEY")
    if not configured(TE_KEY): missing.append("TRADING_ECONOMICS_API_KEY")
    if not configured(TG_TOKEN): missing.append("TELEGRAM_BOT_TOKEN")
    if not configured(TG_CHAT): missing.append("TELEGRAM_CHAT_ID")
    return {"ready": not missing, "missing": missing}


@app.get("/providers/status")
def providers_status():
    return {
        "market_feed": configured(TD_KEY),
        "economic_calendar": configured(TE_KEY),
        "telegram": configured(TG_TOKEN) and configured(TG_CHAT),
        "secrets_exposed": False,
    }


@app.get("/silver")
def silver():
    try:
        xag = td_price("XAG/USD")
        fx = td_price("USD/INR")
        if xag is None or fx is None:
            return {"confirmed": False, "message": "DATA NOT CONFIRMED", "xag_usd": xag, "usd_inr": fx}
        parity = parity_inr_kg(xag, fx)
        return {"confirmed": True, "xag_usd": xag, "usd_inr": fx, "indicative_inr_per_kg": round(parity, 2), "note": "Indicative international parity; not MCX/retail physical price."}
    except Exception as e:
        return {"confirmed": False, "message": "DATA NOT CONFIRMED", "error": type(e).__name__}


@app.get("/mysilver")
def my_silver():
    try:
        xag = td_price("XAG/USD")
        fx = td_price("USD/INR")
        if xag is None or fx is None:
            return {"confirmed": False, "message": "DATA NOT CONFIRMED", "quantity_kg": SILVER_KG, "avg_cost_inr_per_kg": AVG_COST}
        px = parity_inr_kg(xag, fx)
        cost = SILVER_KG * AVG_COST
        value = SILVER_KG * px
        pnl = value - cost
        return {"confirmed": True, "quantity_kg": SILVER_KG, "avg_cost_inr_per_kg": AVG_COST, "cost_basis_inr": round(cost,2), "indicative_value_inr": round(value,2), "unrealised_pnl_inr": round(pnl,2), "unrealised_pnl_pct": round((pnl/cost)*100,2), "pricing_note": "Uses international parity, not local dealer/MCX execution price."}
    except Exception as e:
        return {"confirmed": False, "message": "DATA NOT CONFIRMED", "error": type(e).__name__}


@app.get("/score")
def score():
    return score_from_change()


@app.post("/telegram/test")
def telegram_test():
    return telegram_send("✅ Market Dost AI is connected. Test alert successful.")


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip().lower()
    chat_id = (msg.get("chat") or {}).get("id")
    if chat_id and configured(TG_TOKEN):
        reply = "Market Dost AI commands: /silver /mysilver /score /status"
        if text == "/silver": reply = str(silver())
        elif text == "/mysilver": reply = str(my_silver())
        elif text == "/score": reply = str(score())
        elif text in ("/start", "/help"): reply = "Namaste! Market Dost AI ready. Commands: /silver /mysilver /score /status"
        elif text == "/status": reply = str(providers_status())
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply}, timeout=12)
    return {"ok": True}


@app.get("/release")
def release():
    return {"version": "2.0.0", "channel": "launch", "timezone": TZ, "timestamp": int(time.time())}
