"""Tests for alert-ingestion-service helper functions and API endpoints."""
import uuid
from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as mod

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Create a test client backed by an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    mod.Base.metadata.create_all(bind=engine)
    _Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    orig_engine = mod.engine
    orig_session = mod.SessionLocal

    mod.engine = engine
    mod.SessionLocal = _Session

    yield TestClient(mod.app)

    mod.engine = orig_engine
    mod.SessionLocal = orig_session


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestNormalizeSeverity:
    def test_valid_values(self):
        assert mod._normalize_severity("critical") == "critical"
        assert mod._normalize_severity("HIGH") == "high"
        assert mod._normalize_severity("  medium  ") == "medium"
        assert mod._normalize_severity("low") == "low"

    def test_aliases(self):
        assert mod._normalize_severity("warn") == "medium"
        assert mod._normalize_severity("warning") == "medium"
        assert mod._normalize_severity("error") == "high"

    def test_unknown_defaults_to_low(self):
        assert mod._normalize_severity("bogus") == "low"
        assert mod._normalize_severity("") == "low"

    def test_none_defaults_to_low(self):
        assert mod._normalize_severity(None) == "low"


class TestParseTimestamp:
    def test_none_returns_now(self):
        result = mod._parse_timestamp(None)
        assert result.tzinfo is not None

    def test_empty_returns_now(self):
        result = mod._parse_timestamp("")
        assert result.tzinfo is not None

    def test_zulu_format(self):
        result = mod._parse_timestamp("2026-01-15T12:00:00Z")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_iso_format(self):
        result = mod._parse_timestamp("2026-06-01T08:30:00+00:00")
        assert result.year == 2026

    def test_naive_gets_utc(self):
        result = mod._parse_timestamp("2026-03-01T10:00:00")
        assert result.tzinfo == UTC

    def test_invalid_returns_now(self):
        result = mod._parse_timestamp("not-a-date")
        assert result.tzinfo is not None


class TestReadSecret:
    def test_reads_from_file(self, monkeypatch, tmp_path):
        f = tmp_path / "sec.txt"
        f.write_text("secret123\n")
        monkeypatch.setenv("X_FILE", str(f))
        monkeypatch.delenv("X", raising=False)
        assert mod._read_secret("X") == "secret123"

    def test_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("X", "env_val")
        monkeypatch.delenv("X_FILE", raising=False)
        assert mod._read_secret("X") == "env_val"


# ---------------------------------------------------------------------------
# API endpoint tests
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
        assert "alerts_received_total" in r.text or "process" in r.text


class TestRootEndpoint:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "alert-ingestion" in r.text


class TestCreateAlert:
    def test_create_alert_stored_only(self, client):
        """When incident-management is unreachable, alert is stored with action=stored_only."""
        r = client.post("/api/v1/alerts", json={
            "service": "test-svc",
            "severity": "high",
            "message": "CPU on fire",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "stored_only"
        assert data["alert_id"] is not None

    def test_create_alert_normalizes_severity(self, client):
        r = client.post("/api/v1/alerts", json={
            "service": "svc",
            "severity": "warning",
            "message": "disk full",
        })
        assert r.status_code == 200

    def test_create_alert_missing_fields(self, client):
        r = client.post("/api/v1/alerts", json={
            "service": "svc",
        })
        assert r.status_code == 422

    def test_create_with_timestamp(self, client):
        r = client.post("/api/v1/alerts", json={
            "service": "svc",
            "severity": "critical",
            "message": "alert",
            "timestamp": "2026-01-15T12:00:00Z",
        })
        assert r.status_code == 200

    def test_create_with_labels(self, client):
        r = client.post("/api/v1/alerts", json={
            "service": "svc",
            "severity": "low",
            "message": "info",
            "labels": {"host": "node-1", "region": "eu"},
        })
        assert r.status_code == 200
        alert_id = r.json()["alert_id"]
        detail = client.get(f"/api/v1/alerts/{alert_id}")
        assert detail.json()["labels"]["host"] == "node-1"


class TestGetAlert:
    def test_get_existing(self, client):
        cr = client.post("/api/v1/alerts", json={
            "service": "svc", "severity": "high", "message": "test"
        })
        alert_id = cr.json()["alert_id"]
        r = client.get(f"/api/v1/alerts/{alert_id}")
        assert r.status_code == 200
        assert r.json()["alert_id"] == alert_id
        assert r.json()["service"] == "svc"
        assert r.json()["severity"] == "high"

    def test_get_nonexistent(self, client):
        r = client.get(f"/api/v1/alerts/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_get_invalid_uuid(self, client):
        r = client.get("/api/v1/alerts/not-a-uuid")
        assert r.status_code == 400
