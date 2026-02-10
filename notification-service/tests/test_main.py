"""Tests for notification-service API endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import VALID_CHANNELS, _read_secret, app


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
