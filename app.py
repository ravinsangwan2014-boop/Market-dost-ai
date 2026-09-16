import os, time, requests, asyncio, threading
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Market Dost AI", version="2.0.0")

# Configuration
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
callback_state_lock = asyncio.Lock()
callback_history_lock = threading.Lock()


class CallbackRequest(BaseModel):
    """Request model for registering callbacks"""
    url: str
    events: List[str] = ["price_change", "pnl_change", "score_change"]
    threshold: Optional[float] = None


def configured(v: str) -> bool:
    """Check if a configuration value is properly set"""
    return bool(v and v.strip())


def td_price(symbol: str) -> Optional[float]:
    """Fetch price data from Twelve Data API"""
    if not configured(TD_KEY):
        logger.warning(f"TWELVE_DATA_API_KEY not configured, cannot fetch {symbol}")
        return None
    try:
        r = requests.get(
            "https://api.twelvedata.com/price",
            params={"symbol": symbol, "apikey": TD_KEY},
            timeout=12
        )
        r.raise_for_status()
        data = r.json()
        if "price" not in data:
            logger.warning(f"No price data found for {symbol}")
            return None
        return float(data["price"])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching price for {symbol}: {str(e)}")
        return None


def telegram_send(text: str) -> dict:
    """Send message via Telegram"""
    if not (configured(TG_TOKEN) and configured(TG_CHAT)):
        logger.warning("Telegram not configured")
        return {"sent": False, "reason": "telegram_not_configured"}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text},
            timeout=12
        )
        return {"sent": r.ok, "status": r.status_code}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return {"sent": False, "reason": str(e)}


def parity_inr_kg(xag_usd: float, usdinr: float) -> float:
    """Calculate silver parity in INR per kg"""
    if xag_usd is None or usdinr is None:
        return 0.0
    return xag_usd * usdinr * 32.1507466


def score_from_change(xag=None, dxy=None, y10=None) -> dict:
    """Generate market score based on available data"""
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


async def trigger_callbacks(event_type: str, payload: dict, callback_urls: Optional[List[str]] = None):
    """Trigger all registered callbacks for a given event type (non-blocking)"""
    if callback_urls is None:
        async with callback_state_lock:
            callback_urls = list(registered_callbacks)

    tasks = []
    for callback_url in callback_urls:
        task = asyncio.create_task(
            invoke_callback(callback_url, event_type, payload)
        )
        tasks.append(task)
    
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Triggered {len(results)} callbacks for event: {event_type}")


async def invoke_callback(
    url: str,
    event_type: str,
    payload: dict
):
    """Invoke a single callback URL"""
    callback_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": payload
    }
    
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(url, json=callback_payload)
        result = {
            "callback_url": url,
            "event": event_type,
            "status": response.status_code,
            "success": response.ok,
            "timestamp": datetime.utcnow().isoformat()
        }
        if response.ok:
            logger.info(f"Callback {url} executed successfully for {event_type}")
        else:
            logger.warning(f"Callback {url} returned status {response.status_code}")
    except Exception as e:
        result = {
            "callback_url": url,
            "event": event_type,
            "status": "error",
            "success": False,
            "error": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.error(f"Callback {url} failed: {str(e)}")
    
    with callback_history_lock:
        callback_history.append(result)
    return result


async def _dispatch_callbacks_without_loop_lock(event_type: str, payload: dict, callback_urls: List[str]):
    """Dispatch callbacks without touching event-loop-bound locks."""
    tasks = []
    for callback_url in callback_urls:
        tasks.append(
            asyncio.create_task(
                invoke_callback(callback_url, event_type, payload)
            )
        )
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _run_callback_dispatch(event_type: str, payload: dict, callback_urls: List[str]):
    """Run callback dispatch in a dedicated event loop."""
    asyncio.run(_dispatch_callbacks_without_loop_lock(event_type, payload, callback_urls))


def schedule_callback_dispatch(event_type: str, payload: dict, callback_urls: Optional[List[str]] = None):
    """Schedule callback dispatch with event-loop fallback."""
    if callback_urls is None:
        callback_urls = list(registered_callbacks)
    if not callback_urls:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(trigger_callbacks(event_type, payload, callback_urls))
        return
    except RuntimeError:
        pass

    thread = threading.Thread(
        target=_run_callback_dispatch,
        args=(event_type, payload, callback_urls),
        daemon=True
    )
    thread.start()


# =====================
# Health & Status Endpoints
# =====================

@app.get("/")
def root():
    """Root endpoint - API status"""
    return {"name": "Market Dost AI", "version": "2.0.0", "status": "running"}


@app.get("/health/live")
def health_live():
    """Liveness probe"""
    return {"ok": True, "service": "market-dost-api"}


@app.get("/health/ready")
def health_ready():
    """Readiness probe - checks if all required configs are set"""
    missing = []
    if not configured(TD_KEY):
        missing.append("TWELVE_DATA_API_KEY")
    if not configured(TE_KEY):
        missing.append("TRADING_ECONOMICS_API_KEY")
    if not configured(TG_TOKEN):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not configured(TG_CHAT):
        missing.append("TELEGRAM_CHAT_ID")
    return {"ready": not missing, "missing": missing}


@app.get("/providers/status")
def providers_status():
    """Check status of all external providers"""
    return {
        "market_feed": configured(TD_KEY),
        "economic_calendar": configured(TE_KEY),
        "telegram": configured(TG_TOKEN) and configured(TG_CHAT),
        "secrets_exposed": False,
    }


# =====================
# Callback Management Endpoints
# =====================

@app.post("/callbacks/register")
async def register_callback(callback: CallbackRequest):
    """Register a callback URL for market events"""
    async with callback_state_lock:
        if callback.url not in registered_callbacks:
            registered_callbacks.append(callback.url)
            logger.info(f"Callback registered: {callback.url}")
        total_callbacks = len(registered_callbacks)
    return {
        "message": "Callback registered",
        "url": callback.url,
        "events": callback.events,
        "total_callbacks": total_callbacks
    }


@app.post("/callbacks/unregister")
async def unregister_callback(url: str):
    """Unregister a callback URL"""
    async with callback_state_lock:
        if url in registered_callbacks:
            registered_callbacks.remove(url)
            logger.info(f"Callback unregistered: {url}")
            return {"message": "Callback unregistered", "url": url}
    return {"message": "Callback not found", "url": url}


@app.get("/callbacks/list")
async def list_callbacks():
    """List all registered callbacks"""
    async with callback_state_lock:
        callbacks = list(registered_callbacks)
        total = len(registered_callbacks)
    return {
        "callbacks": callbacks,
        "total": total
    }


@app.get("/callbacks/history")
async def get_callback_history(limit: int = 50):
    """Get callback invocation history"""
    with callback_history_lock:
        history = callback_history[-limit:]
        total = len(callback_history)
    return {
        "history": history,
        "total": total
    }


# =====================
# Market Data Endpoints
# =====================

@app.get("/silver")
async def silver():
    """Get current silver price in USD and parity in INR per kg"""
    try:
        xag = td_price("XAG/USD")
        fx = td_price("USD/INR")
        if xag is None or fx is None:
            return {
                "confirmed": False,
                "message": "DATA NOT CONFIRMED",
                "xag_usd": xag,
                "usd_inr": fx
            }
        parity = parity_inr_kg(xag, fx)
        
        # Trigger callbacks (non-blocking)
        async with callback_state_lock:
            callback_urls = list(registered_callbacks)
        if callback_urls:
            schedule_callback_dispatch("price_change", {
                "xag_usd": xag,
                "usd_inr": fx,
                "indicative_inr_per_kg": round(parity, 2)
            }, callback_urls)
        
        return {
            "confirmed": True,
            "xag_usd": xag,
            "usd_inr": fx,
            "indicative_inr_per_kg": round(parity, 2),
            "note": "Indicative international parity; not MCX/retail physical price."
        }
    except Exception as e:
        logger.error(f"Error in /silver endpoint: {str(e)}")
        return {
            "confirmed": False,
            "message": "DATA NOT CONFIRMED",
            "error": type(e).__name__
        }


@app.get("/mysilver")
async def my_silver():
    """Get personal silver portfolio P&L"""
    try:
        xag = td_price("XAG/USD")
        fx = td_price("USD/INR")
        if xag is None or fx is None:
            return {
                "confirmed": False,
                "message": "DATA NOT CONFIRMED",
                "quantity_kg": SILVER_KG,
                "avg_cost_inr_per_kg": AVG_COST
            }
        px = parity_inr_kg(xag, fx)
        cost = SILVER_KG * AVG_COST
        value = SILVER_KG * px
        pnl = value - cost
        
        # Trigger callbacks (non-blocking)
        async with callback_state_lock:
            callback_urls = list(registered_callbacks)
        if callback_urls:
            schedule_callback_dispatch("pnl_change", {
                "quantity_kg": SILVER_KG,
                "cost_basis_inr": round(cost, 2),
                "indicative_value_inr": round(value, 2),
                "unrealised_pnl_inr": round(pnl, 2)
            }, callback_urls)
        
        return {
            "confirmed": True,
            "quantity_kg": SILVER_KG,
            "avg_cost_inr_per_kg": AVG_COST,
            "cost_basis_inr": round(cost, 2),
            "indicative_value_inr": round(value, 2),
            "unrealised_pnl_inr": round(pnl, 2),
            "pnl_percentage": round((pnl / cost * 100), 2) if cost > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error in /mysilver endpoint: {str(e)}")
        return {
            "confirmed": False,
            "message": "DATA NOT CONFIRMED",
            "error": type(e).__name__
        }


@app.get("/score")
async def score():
    """Get current market score and bias"""
    try:
        score_data = score_from_change()
        
        # Trigger callbacks (non-blocking)
        async with callback_state_lock:
            callback_urls = list(registered_callbacks)
        if callback_urls:
            schedule_callback_dispatch("score_change", score_data, callback_urls)
        
        return score_data
    except Exception as e:
        logger.error(f"Error in /score endpoint: {str(e)}")
        return {
            "score": 50,
            "bias": "Neutral",
            "confidence": "LOW",
            "error": type(e).__name__
        }


# =====================
# Telegram Endpoints
# =====================

@app.post("/telegram/test")
def telegram_test():
    """Test Telegram bot connectivity"""
    return telegram_send("✅ Market Dost AI is connected. Test alert successful.")


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook receiver for bot commands"""
    try:
        update = await request.json()
        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip().lower()
        chat_id = (msg.get("chat") or {}).get("id")
        
        if chat_id and configured(TG_TOKEN):
            reply = "Market Dost AI commands: /silver /mysilver /score /status"
            
            if text == "/silver":
                reply = str(await silver())
            elif text == "/mysilver":
                reply = str(await my_silver())
            elif text == "/score":
                reply = str(await score())
            elif text in ("/start", "/help"):
                reply = "Namaste! Market Dost AI ready. Commands: /silver /mysilver /score /status"
            elif text == "/status":
                reply = str(providers_status())
            
            async with httpx.AsyncClient(timeout=12.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": reply}
                )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error in telegram webhook: {str(e)}")
        return {"ok": False, "error": str(e)}


# =====================
# Release Info Endpoint
# =====================

@app.get("/release")
def release():
    """Get release information"""
    return {
        "version": "2.0.0",
        "channel": "launch",
        "timezone": TZ,
        "timestamp": int(time.time())
    }
