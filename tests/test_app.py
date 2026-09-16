"""
Unit tests for Market Dost AI application
"""
import pytest
import asyncio
import app as app_module
from fastapi.testclient import TestClient
from app import app, registered_callbacks, callback_history

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_callback_state():
    registered_callbacks.clear()
    with app_module.callback_history_lock:
        callback_history.clear()
    yield
    registered_callbacks.clear()
    with app_module.callback_history_lock:
        callback_history.clear()


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Market Dost AI"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"

    def test_health_live(self):
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["service"] == "market-dost-api"

    def test_health_ready(self):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "missing" in data


class TestProvidersStatus:
    """Test provider status endpoint"""

    def test_providers_status(self):
        response = client.get("/providers/status")
        assert response.status_code == 200
        data = response.json()
        assert "market_feed" in data
        assert "economic_calendar" in data
        assert "telegram" in data
        assert "secrets_exposed" in data
        assert data["secrets_exposed"] is False


class TestCallbackManagement:
    """Test callback registration and management"""

    def test_register_callback(self):
        test_url = "https://example.com/webhook"
        response = client.post(
            "/callbacks/register",
            json={"url": test_url, "events": ["price_change"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Callback registered"
        assert data["url"] == test_url

    def test_list_callbacks(self):
        response = client.get("/callbacks/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["callbacks"], list)
        assert "total" in data

    def test_unregister_callback(self):
        test_url = "https://example.com/webhook"
        # First register
        client.post("/callbacks/register", json={"url": test_url})
        # Then unregister
        response = client.post("/callbacks/unregister", params={"url": test_url})
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Callback unregistered"

    def test_unregister_callback_from_body(self):
        test_url = "https://example.com/body-webhook"
        client.post("/callbacks/register", json={"url": test_url})
        response = client.post("/callbacks/unregister", json={"url": test_url})
        assert response.status_code == 200
        assert response.json()["message"] == "Callback unregistered"

    def test_callback_history(self):
        response = client.get("/callbacks/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["history"], list)
        assert "total" in data

    def test_invoke_callback_uses_httpx_success_flag(self, monkeypatch):
        class DummyAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json):
                return type(
                    "Resp",
                    (),
                    {
                        "is_success": True,
                        "status_code": 200,
                    },
                )()

        monkeypatch.setattr(
            app_module.httpx,
            "AsyncClient",
            lambda *args, **kwargs: DummyAsyncClient(),
        )

        result = asyncio.run(
            app_module.invoke_callback(
                "https://example.com/callback",
                "price_change",
                {"xag_usd": 31.0},
            )
        )

        assert result["success"] is True
        assert result["status"] == 200


class TestMarketDataEndpoints:
    """Test market data endpoints"""

    def test_silver_endpoint(self):
        response = client.get("/silver")
        assert response.status_code == 200
        data = response.json()
        assert "confirmed" in data
        assert "message" in data
        # Data may not be confirmed without API key
        if data["confirmed"]:
            assert "xag_usd" in data
            assert "usd_inr" in data
            assert "indicative_inr_per_kg" in data

    def test_mysilver_endpoint(self):
        response = client.get("/mysilver")
        assert response.status_code == 200
        data = response.json()
        assert "confirmed" in data
        assert "message" in data
        assert "quantity_kg" in data
        assert "avg_cost_inr_per_kg" in data

    def test_score_endpoint(self):
        response = client.get("/score")
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "bias" in data
        assert "confidence" in data
        assert "reasons" in data


class TestReleaseEndpoint:
    """Test release information endpoint"""

    def test_release_endpoint(self):
        response = client.get("/release")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["channel"] == "launch"
        assert "timezone" in data
        assert "timestamp" in data
        assert isinstance(data["timestamp"], int)


class TestTelegramEndpoints:
    """Test Telegram endpoints"""

    def test_telegram_test(self):
        response = client.post("/telegram/test")
        assert response.status_code == 200
        data = response.json()
        assert "sent" in data
        # May fail if not configured, but endpoint should work

    def test_telegram_webhook(self):
        response = client.post(
            "/telegram/webhook",
            json={
                "message": {
                    "text": "/silver",
                    "chat": {"id": 12345}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_telegram_webhook_silver_command_async_path(self, monkeypatch):
        async def fake_silver():
            return {"confirmed": True, "xag_usd": 31.0}

        class DummyAsyncClient:
            def __init__(self, *args, **kwargs):
                self.post_calls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json):
                self.post_calls.append((url, json))
                return type(
                    "Resp",
                    (),
                    {
                        "ok": True,
                        "status_code": 200,
                        "raise_for_status": lambda self: None,
                    },
                )()

        dummy_client = DummyAsyncClient()
        monkeypatch.setattr(app_module, "silver", fake_silver)
        monkeypatch.setattr(app_module, "TG_TOKEN", "token")
        monkeypatch.setattr(
            app_module.httpx,
            "AsyncClient",
            lambda *args, **kwargs: dummy_client,
        )

        response = client.post(
            "/telegram/webhook",
            json={"message": {"text": "/silver", "chat": {"id": 12345}}},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert dummy_client.post_calls
        _, sent_payload = dummy_client.post_calls[0]
        assert sent_payload["chat_id"] == 12345
        assert "xag_usd" in sent_payload["text"]

    def test_telegram_webhook_returns_error_on_async_post_failure(self, monkeypatch):
        class FailingAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json):
                raise RuntimeError("send failed")

        monkeypatch.setattr(app_module, "TG_TOKEN", "token")
        monkeypatch.setattr(
            app_module.httpx,
            "AsyncClient",
            lambda *args, **kwargs: FailingAsyncClient(),
        )

        response = client.post(
            "/telegram/webhook",
            json={"message": {"text": "/status", "chat": {"id": 12345}}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "send failed" in data["error"]


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_callback_unregister(self):
        response = client.post(
            "/callbacks/unregister",
            params={"url": "https://nonexistent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Callback not found"


class TestAsyncScheduling:
    def test_callback_routes_are_async(self):
        assert asyncio.iscoroutinefunction(app_module.silver)
        assert asyncio.iscoroutinefunction(app_module.my_silver)
        assert asyncio.iscoroutinefunction(app_module.score)

    def test_schedule_callback_dispatch_with_running_loop(self, monkeypatch):
        seen = {}

        async def run_test():
            event = asyncio.Event()

            async def fake_trigger_callbacks(event_type, payload, callback_urls=None):
                seen["event_type"] = event_type
                seen["payload"] = payload
                seen["callback_urls"] = callback_urls
                event.set()

            monkeypatch.setattr(app_module, "trigger_callbacks", fake_trigger_callbacks)
            monkeypatch.setattr(
                app_module.threading,
                "Thread",
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    AssertionError("Thread fallback should not be used when loop is running")
                ),
            )

            registered_callbacks.append("https://example.com/loop")
            app_module.schedule_callback_dispatch(
                "score_change",
                {"score": 50},
                list(registered_callbacks),
            )
            await asyncio.wait_for(event.wait(), timeout=1)

        asyncio.run(run_test())
        assert seen["event_type"] == "score_change"
        assert seen["payload"]["score"] == 50
        assert seen["callback_urls"] == ["https://example.com/loop"]

    def test_schedule_callback_dispatch_without_running_loop(self, monkeypatch):
        seen = {}

        async def fake_invoke_callback(url, event_type, payload, use_async_state_lock=True):
            seen["url"] = url
            seen["event_type"] = event_type
            seen["payload"] = payload

        class DummyThread:
            def __init__(self, target=None, args=(), daemon=False):
                self._target = target
                self._args = args
                self.daemon = daemon
                seen["daemon"] = daemon

            def start(self):
                self._target(*self._args)

        monkeypatch.setattr(app_module, "invoke_callback", fake_invoke_callback)
        monkeypatch.setattr(app_module.threading, "Thread", DummyThread)
        registered_callbacks.append("https://example.com/webhook")

        app_module.schedule_callback_dispatch(
            "price_change",
            {"xag_usd": 30.0},
            list(registered_callbacks),
        )

        assert seen["url"] == "https://example.com/webhook"
        assert seen["event_type"] == "price_change"
        assert seen["payload"]["xag_usd"] == 30.0
        assert seen["daemon"] is False

    def test_register_callback_waits_on_state_lock(self):
        async def run_test():
            callback_url = "https://example.com/lock-test"

            async with app_module.callback_state_lock:
                task = asyncio.create_task(
                    app_module.register_callback(app_module.CallbackRequest(url=callback_url))
                )
                await asyncio.sleep(0)
                assert callback_url not in registered_callbacks

            result = await asyncio.wait_for(task, timeout=1)
            assert result["message"] == "Callback registered"
            assert callback_url in registered_callbacks

        asyncio.run(run_test())

    def test_silver_offloads_price_fetches_with_to_thread(self, monkeypatch):
        seen = []

        async def fake_to_thread(func, symbol):
            seen.append((func, symbol))
            return {"XAG/USD": 31.0, "USD/INR": 84.0}[symbol]

        monkeypatch.setattr(app_module.asyncio, "to_thread", fake_to_thread)

        result = asyncio.run(app_module.silver())

        assert seen == [
            (app_module.td_price, "XAG/USD"),
            (app_module.td_price, "USD/INR"),
        ]
        assert result["confirmed"] is True

    def test_mysilver_offloads_price_fetches_with_to_thread(self, monkeypatch):
        seen = []

        async def fake_to_thread(func, symbol):
            seen.append((func, symbol))
            return {"XAG/USD": 31.0, "USD/INR": 84.0}[symbol]

        monkeypatch.setattr(app_module.asyncio, "to_thread", fake_to_thread)

        result = asyncio.run(app_module.my_silver())

        assert seen == [
            (app_module.td_price, "XAG/USD"),
            (app_module.td_price, "USD/INR"),
        ]
        assert result["confirmed"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
