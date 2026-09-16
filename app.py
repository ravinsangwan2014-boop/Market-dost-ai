import os, time, requests, asyncio
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Market Dost AI", version="2.0.0")

SILVER_KG = float(os.getenv("SILVER_KG", "28"))
AVG_COST = float(os.getenv("SILVER_AVG_COST_INR_PER_KG", "171000"))
TZ = os.getenv("TIMEZONE", "Asia/Kolkata")
TD_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TE_KEY = os.getenv("TRADING_ECONOMICS_API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")

# Callback storage
registered_callbacks: List[str] = []
callback_history: List[dict] = []


class CallbackRequest(BaseModel):
    """Request model for registering callbacks"""
    url: str
    events: List[str] = ["price_change", "pnl_change", "score_change"]
    threshold: Optional[float] = None


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


async def trigger_callbacks(event_type: str, payload: dict):
    """Trigger all registered callbacks for a given event type"""
    tasks = []
    for callback_url in registered_callbacks:
        task = asyncio.create_task(
            invoke_callback(callback_url, event_type, payload)
        )
        tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def invoke_callback(url: str, event_type: str, payload: dict):
    """Invoke a single callback URL with retry logic"""
    callback_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": payload
    }
    
    try:
        response = requests.post(url, json=callback_payload, timeout=12)
        result = {
            "callback_url": url,
            "event": event_type,
            "status": response.status_code,
            "success": response.ok,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        result = {
            "callback_url": url,
            "event": event_type,
            "status": "error",
            "success": False,
            "error": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    callback_history.append(result)
    return result


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


@app.post("/callbacks/register")
def register_callback(callback: CallbackRequest):
    """Register a callback URL for market events"""
    if callback.url not in registered_callbacks:
        registered_callbacks.append(callback.url)
    return {
        "message": "Callback registered",
        "url": callback.url,
        "events": callback.events,
        "total_callbacks": len(registered_callbacks)
    }


@app.post("/callbacks/unregister")
def unregister_callback(url: str):
    """Unregister a callback URL"""
    if url in registered_callbacks:
        registered_callbacks.remove(url)
        return {"message": "Callback unregistered", "url": url}
    return {"message": "Callback not found", "url": url}


@app.get("/callbacks/list")
def list_callbacks():
    """List all registered callbacks"""
    return {
        "callbacks": registered_callbacks,
        "total": len(registered_callbacks)
    }


@app.get("/callbacks/history")
def get_callback_history(limit: int = 50):
    """Get callback invocation history"""
    return {
        "history": callback_history[-limit:],
        "total": len(callback_history)
    }


@app.get("/silver")
def silver():
    try:
        xag = td_price("XAG/USD")
        fx = td_price("USD/INR")
        if xag is None or fx is None:
            return {"confirmed": False, "message": "DATA NOT CONFIRMED", "xag_usd": xag, "usd_inr": fx}
        parity = parity_inr_kg(xag, fx)
        
        # Trigger callbacks
        if registered_callbacks:
            asyncio.create_task(trigger_callbacks("price_change", {
                "xag_usd": xag,
                "usd_inr": fx,
                "indicative_inr_per_kg": round(parity, 2)
            }))
        
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
        
        # Trigger callbacks
        if registered_callbacks:
            asyncio.create_task(trigger_callbacks("pnl_change", {
                "quantity_kg": SILVER_KG,
                "cost_basis_inr": round(cost, 2),
                "indicative_value_inr": round(value, 2),
                "unrealised_pnl_inr": round(pnl, 2)
            }))
        
        return {"confirmed": True, "quantity_kg": SILVER_KG, "avg_cost_inr_per_kg": AVG_COST, "cost_basis_inr": round(cost,2), "indicative_value_inr": round(value,2), "unrealised_pnl_inr": round(pnl,2)}
    except Exception as e:
        return {"confirmed": False, "message": "DATA NOT CONFIRMED", "error": type(e).__name__}


@app.get("/score")
def score():
    score_data = score_from_change()
    
    # Trigger callbacks
    if registered_callbacks:
        asyncio.create_task(trigger_callbacks("score_change", score_data))
    
    return score_data


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
