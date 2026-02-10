"""Tests for notification-service API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import VALID_CHANNELS, _read_secret, app
from app.tracing import init_tracing


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestReadSecret:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "val")
        monkeypatch.delenv("TEST_KEY_FILE", raising=False)
        assert _read_secret("TEST_KEY") == "val"

    def test_from_file(self, monkeypatch, tmp_path):
        f = tmp_path / "s.txt"
        f.write_text("file_val\n")
        monkeypatch.setenv("TEST_KEY_FILE", str(f))
        monkeypatch.delenv("TEST_KEY", raising=False)
        assert _read_secret("TEST_KEY") == "file_val"

    def test_default(self, monkeypatch):
        monkeypatch.delenv("NOPE", raising=False)
        monkeypatch.delenv("NOPE_FILE", raising=False)
        assert _read_secret("NOPE", "default") == "default"


class TestValidChannels:
    def test_channels(self):
        assert "mock" in VALID_CHANNELS
        assert "email" in VALID_CHANNELS
        assert "webhook" in VALID_CHANNELS
        assert "slack" in VALID_CHANNELS


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestMetricsEndpoint:
    def test_metrics(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200


class TestNotify:
    def test_mock_channel(self, client):
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-123",
            "message": "Test notification",
            "channel": "mock",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "sent"
        assert data["channel"] == "mock"

    def test_default_channel_is_mock(self, client):
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-456",
            "message": "Default channel test",
        })
        assert r.status_code == 201
        assert r.json()["channel"] == "mock"

    def test_invalid_channel(self, client):
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-789",
            "message": "Bad channel",
            "channel": "pigeon",
        })
        assert r.status_code == 422

    def test_missing_incident_id(self, client):
        r = client.post("/api/v1/notify", json={
            "message": "no id",
        })
        assert r.status_code == 422

    def test_missing_message(self, client):
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-1",
        })
        assert r.status_code == 422

    def test_email_channel_no_key(self, client, monkeypatch):
        """Email channel with no API key should still succeed (logged but not sent)."""
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-email",
            "message": "Email test",
            "channel": "email",
        })
        assert r.status_code == 201

    def test_webhook_no_target(self, client):
        """Webhook with no target URL should still succeed (logged only)."""
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-wh",
            "message": "Webhook test",
            "channel": "webhook",
        })
        assert r.status_code == 201

    def test_slack_channel(self, client):
        """Slack channel works like mock (logged)."""
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-slack",
            "message": "Slack test",
            "channel": "slack",
        })
        assert r.status_code == 201


class TestReadSecretEdge:
    def test_file_not_found_falls_back(self, monkeypatch):
        monkeypatch.setenv("X_FILE", "/nonexistent/path/secret.txt")
        monkeypatch.setenv("X", "env_fallback")
        assert _read_secret("X") == "env_fallback"

    def test_file_not_found_no_env(self, monkeypatch):
        monkeypatch.setenv("Y_FILE", "/nonexistent/path")
        monkeypatch.delenv("Y", raising=False)
        assert _read_secret("Y") == ""


class TestNotifyEdge:
    def test_email_with_placeholder_key(self, client, monkeypatch):
        """Email channel with PLACEHOLDER key should log warning but still succeed."""
        monkeypatch.setenv("RESEND_API_KEY", "PLACEHOLDER_KEY")
        monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-ph",
            "message": "Placeholder email test",
            "channel": "email",
        })
        assert r.status_code == 201

    def test_email_with_real_key_success(self, client, monkeypatch):
        """Email channel with a real key should call Resend API."""
        monkeypatch.setenv("RESEND_API_KEY", "re_real_key_123")
        monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = lambda: None
        mock_response.json = lambda: {"id": "email-123"}

        with patch("app.main.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.post("/api/v1/notify", json={
                "incident_id": "inc-email-real",
                "message": "Real email test",
                "channel": "email",
                "target": "user@example.com",
            })
            assert r.status_code == 201

    def test_webhook_with_valid_url(self, client):
        """Webhook with a valid URL should attempt delivery."""
        with patch("app.main.httpx.AsyncClient") as MockClient:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = lambda: None

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.post("/api/v1/notify", json={
                "incident_id": "inc-wh-url",
                "message": "Webhook with URL",
                "channel": "webhook",
                "target": "http://example.com/webhook",
            })
            assert r.status_code == 201

    def test_webhook_invalid_target(self, client):
        """Webhook with non-http target is logged only."""
        r = client.post("/api/v1/notify", json={
            "incident_id": "inc-wh-bad",
            "message": "Bad target",
            "channel": "webhook",
            "target": "not-a-url",
        })
        assert r.status_code == 201

    def test_email_delivery_http_error(self, client, monkeypatch):
        """Email delivery failure returns 502."""
        import httpx as _httpx
        monkeypatch.setenv("RESEND_API_KEY", "re_real_key_456")
        monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)

        with patch("app.main.httpx.AsyncClient") as MockClient:
            mock_response = AsyncMock()
            mock_response.status_code = 500

            def _raise():
                raise _httpx.HTTPStatusError(
                    "Server Error",
                    request=_httpx.Request("POST", "https://api.resend.com/emails"),
                    response=_httpx.Response(500),
                )
            mock_response.raise_for_status = _raise

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.post("/api/v1/notify", json={
                "incident_id": "inc-fail",
                "message": "Fail email",
                "channel": "email",
            })
            assert r.status_code == 502

    def test_generic_exception_returns_500(self, client, monkeypatch):
        """Generic exception during delivery returns 500."""
        monkeypatch.setenv("RESEND_API_KEY", "re_real_key_789")
        monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)

        with patch("app.main.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = RuntimeError("Connection refused")
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.post("/api/v1/notify", json={
                "incident_id": "inc-generic-fail",
                "message": "Generic fail",
                "channel": "email",
            })
            assert r.status_code == 500


class TestTracing:
    def test_tracing_disabled_without_endpoint(self, monkeypatch):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        init_tracing(app)  # should be a no-op

    def test_tracing_import_error(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://fake:4317")
        # This will either succeed (if otel is installed) or hit ImportError
        init_tracing(app)
