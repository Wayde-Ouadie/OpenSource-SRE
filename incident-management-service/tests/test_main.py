"""Tests for incident-management-service helper functions and API endpoints."""
import uuid
from datetime import UTC, datetime, timedelta

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
    """Create a test client backed by an in-memory SQLite database.

    We swap the module-level engine/SessionLocal with a StaticPool SQLite
    engine so that all connections share the same in-memory database.
    """
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

    # Patch out the oncall/notification calls
    async def _noop(*args, **kwargs):
        return None

    orig_lookup = mod._lookup_oncall_and_notify
    mod._lookup_oncall_and_notify = _noop

    yield TestClient(mod.app)

    mod.engine = orig_engine
    mod.SessionLocal = orig_session
    mod._lookup_oncall_and_notify = orig_lookup


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestReadSecret:
    def test_read_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "env_value")
        assert mod._read_secret("MY_SECRET") == "env_value"

    def test_read_from_file(self, monkeypatch, tmp_path):
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("file_value\n")
        monkeypatch.setenv("MY_SECRET_FILE", str(secret_file))
        monkeypatch.delenv("MY_SECRET", raising=False)
        assert mod._read_secret("MY_SECRET") == "file_value"

    def test_default_when_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_SECRET", raising=False)
        monkeypatch.delenv("MISSING_SECRET_FILE", raising=False)
        assert mod._read_secret("MISSING_SECRET", "fallback") == "fallback"

    def test_file_not_found_falls_back(self, monkeypatch):
        monkeypatch.setenv("BAD_FILE_FILE", "/nonexistent/path")
        monkeypatch.setenv("BAD_FILE", "env_val")
        assert mod._read_secret("BAD_FILE") == "env_val"


class TestFmtDt:
    def test_formats_datetime(self):
        dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        assert mod._fmt_dt(dt) == "2026-01-15T12:00:00Z"

    def test_none_returns_none(self):
        assert mod._fmt_dt(None) is None


class TestAppendTimeline:
    def test_appends_to_empty(self):
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="open",
            timeline=[],
        )
        mod._append_timeline(inc, "created", "test detail", "alice")
        assert len(inc.timeline) == 1
        assert inc.timeline[0]["type"] == "created"
        assert inc.timeline[0]["actor"] == "alice"

    def test_appends_to_existing(self):
        existing = [{"id": "old", "type": "note", "detail": "x", "actor": "bob", "timestamp": "t"}]
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="open",
            timeline=existing,
        )
        mod._append_timeline(inc, "resolved", "done")
        assert len(inc.timeline) == 2

    def test_none_timeline_becomes_list(self):
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="open",
            timeline=None,
        )
        mod._append_timeline(inc, "created", "init")
        assert len(inc.timeline) == 1


class TestCalculateMetrics:
    def test_no_ack_no_resolve(self):
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="open",
            created_at=datetime.now(UTC),
        )
        m = mod._calculate_metrics(inc)
        assert m["mtta_seconds"] is None
        assert m["mttr_seconds"] is None

    def test_with_ack(self):
        now = datetime.now(UTC)
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="acknowledged",
            created_at=now - timedelta(minutes=5),
            acknowledged_at=now,
        )
        m = mod._calculate_metrics(inc)
        assert m["mtta_seconds"] == pytest.approx(300, abs=2)
        assert m["mttr_seconds"] is None

    def test_with_resolve(self):
        now = datetime.now(UTC)
        inc = mod.Incident(
            service="svc", severity="high", title="t", status="resolved",
            created_at=now - timedelta(hours=1),
            acknowledged_at=now - timedelta(minutes=50),
            resolved_at=now,
        )
        m = mod._calculate_metrics(inc)
        assert m["mtta_seconds"] == pytest.approx(600, abs=2)
        assert m["mttr_seconds"] == pytest.approx(3600, abs=2)


class TestValidSeverities:
    def test_contains_expected(self):
        assert {"critical", "high", "medium", "low"} == mod.VALID_SEVERITIES


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
        assert "incidents_total" in r.text or "process" in r.text


class TestRootEndpoint:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "incident-management"


class TestCreateIncident:
    def test_create_basic(self, client):
        r = client.post("/api/v1/incidents", json={
            "service": "test-svc",
            "severity": "high",
            "title": "Test incident",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "test-svc"
        assert data["severity"] == "high"
        assert data["status"] == "open"
        assert "id" in data

    def test_create_normalizes_severity(self, client):
        r = client.post("/api/v1/incidents", json={
            "service": "svc",
            "severity": "UNKNOWN",
            "title": "t",
        })
        assert r.status_code == 200
        assert r.json()["severity"] == "medium"

    def test_create_missing_title_fails(self, client):
        r = client.post("/api/v1/incidents", json={
            "service": "svc",
            "severity": "high",
        })
        assert r.status_code == 422


class TestListIncidents:
    def test_list_empty(self, client):
        r = client.get("/api/v1/incidents")
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_list_after_create(self, client):
        client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t1"
        })
        r = client.get("/api/v1/incidents")
        assert r.json()["count"] == 1

    def test_filter_by_status(self, client):
        client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t1"
        })
        r = client.get("/api/v1/incidents?status=resolved")
        assert r.json()["count"] == 0

    def test_filter_by_service(self, client):
        client.post("/api/v1/incidents", json={
            "service": "alpha", "severity": "low", "title": "a"
        })
        client.post("/api/v1/incidents", json={
            "service": "beta", "severity": "low", "title": "b"
        })
        r = client.get("/api/v1/incidents?service=alpha")
        assert r.json()["count"] == 1


class TestGetIncident:
    def test_get_existing(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        r = client.get(f"/api/v1/incidents/{inc_id}")
        assert r.status_code == 200
        assert r.json()["id"] == inc_id
        assert "timeline" in r.json()

    def test_get_nonexistent(self, client):
        r = client.get(f"/api/v1/incidents/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_get_invalid_uuid(self, client):
        r = client.get("/api/v1/incidents/not-a-uuid")
        assert r.status_code == 400


class TestUpdateIncident:
    def test_acknowledge(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        r = client.patch(f"/api/v1/incidents/{inc_id}", json={"status": "acknowledged"})
        assert r.status_code == 200
        assert r.json()["status"] == "acknowledged"

    def test_resolve(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        client.patch(f"/api/v1/incidents/{inc_id}", json={"status": "acknowledged"})
        r = client.patch(f"/api/v1/incidents/{inc_id}", json={"status": "resolved"})
        assert r.status_code == 200
        assert r.json()["status"] == "resolved"

    def test_assign(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        r = client.patch(f"/api/v1/incidents/{inc_id}", json={"assigned_to": "alice"})
        assert r.status_code == 200
        assert r.json()["assigned_to"] == "alice"

    def test_update_nonexistent(self, client):
        r = client.patch(f"/api/v1/incidents/{uuid.uuid4()}", json={"status": "open"})
        assert r.status_code == 404


class TestGetIncidentMetrics:
    def test_metrics_after_resolve(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        client.patch(f"/api/v1/incidents/{inc_id}", json={"status": "acknowledged"})
        client.patch(f"/api/v1/incidents/{inc_id}", json={"status": "resolved"})
        r = client.get(f"/api/v1/incidents/{inc_id}/metrics")
        assert r.status_code == 200
        data = r.json()
        assert data["mtta_seconds"] is not None
        assert data["mttr_seconds"] is not None


class TestAddNote:
    def test_add_note(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        r = client.post(f"/api/v1/incidents/{inc_id}/notes", json={
            "content": "Investigation started", "author": "bob"
        })
        assert r.status_code == 200
        assert r.json()["note"]["content"] == "Investigation started"

    def test_note_appears_in_incident(self, client):
        cr = client.post("/api/v1/incidents", json={
            "service": "svc", "severity": "high", "title": "t"
        })
        inc_id = cr.json()["id"]
        client.post(f"/api/v1/incidents/{inc_id}/notes", json={
            "content": "note1", "author": "a"
        })
        r = client.get(f"/api/v1/incidents/{inc_id}")
        assert len(r.json()["notes"]) == 1

    def test_note_on_nonexistent_incident(self, client):
        r = client.post(f"/api/v1/incidents/{uuid.uuid4()}/notes", json={
            "content": "x", "author": "a"
        })
        assert r.status_code == 404
