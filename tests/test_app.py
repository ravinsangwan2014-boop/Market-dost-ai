"""
Unit tests for Market Dost AI application
"""
import app as app_module
import pytest
from fastapi.testclient import TestClient
from app import app, registered_callbacks, callback_history

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_callback_state():
    registered_callbacks.clear()
    callback_history.clear()
    yield
    registered_callbacks.clear()
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

    def test_callback_history(self):
        response = client.get("/callbacks/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["history"], list)
        assert "total" in data

    def test_silver_schedules_callbacks_without_running_loop(self, monkeypatch):
        calls = []

        async def fake_trigger(event_type, payload):
            calls.append((event_type, payload))

        class ImmediateThread:
            def __init__(self, target=None, args=(), kwargs=None, daemon=None):
                self.target = target
                self.args = args
                self.kwargs = kwargs or {}

            def start(self):
                self.target(*self.args, **self.kwargs)

        registered_callbacks.append("https://example.com/webhook")
        monkeypatch.setattr(app_module, "td_price", lambda symbol: 32.5 if symbol == "XAG/USD" else 86.0)
        monkeypatch.setattr(app_module, "trigger_callbacks", fake_trigger)
        monkeypatch.setattr(app_module.threading, "Thread", ImmediateThread)

        response = client.get("/silver")

        assert response.status_code == 200
        assert response.json()["confirmed"] is True
        assert calls == [(
            "price_change",
            {
                "xag_usd": 32.5,
                "usd_inr": 86.0,
                "indicative_inr_per_kg": 89861.34,
            },
        )]


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
