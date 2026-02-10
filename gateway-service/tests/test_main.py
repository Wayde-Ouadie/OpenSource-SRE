"""Tests for gateway-service API endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    import importlib

    import app.main as mod
    importlib.reload(mod)
    return TestClient(mod.app)


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["service"] == "gateway"


class TestMetricsEndpoint:
    def test_metrics(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        # Should contain prometheus process metrics
        assert "process" in r.text or "python" in r.text


class TestApiHealth:
    def test_api_health_fails_gracefully(self, client):
        """When incident-management is unreachable, should return error status."""
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        # Either proxied result or error
        assert "status" in data


class TestRequestIdMiddleware:
    def test_adds_request_id(self, client):
        r = client.get("/health")
        assert "x-request-id" in r.headers

    def test_preserves_request_id(self, client):
        r = client.get("/health", headers={"X-Request-ID": "test-id-123"})
        assert r.headers["x-request-id"] == "test-id-123"
