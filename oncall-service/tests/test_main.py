"""Tests for oncall-service helper functions and API endpoints."""
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
    # SQLite does not support schema-qualified table names; strip them.
    for table in mod.Base.metadata.tables.values():
        table.schema = None
    mod.Base.metadata.create_all(bind=engine)
    _Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    orig_engine = mod.engine
    orig_session = mod.SessionLocal

    mod.engine = engine
    mod.SessionLocal = _Session
    mod._escalated_incidents.clear()

    yield TestClient(mod.app)

    mod.engine = orig_engine
    mod.SessionLocal = orig_session


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_none_returns_now(self):
        result = mod._parse_dt(None)
        assert result.tzinfo is not None

    def test_zulu(self):
        result = mod._parse_dt("2026-01-15T12:00:00Z")
        assert result.year == 2026

    def test_iso(self):
        result = mod._parse_dt("2026-01-15T12:00:00+00:00")
        assert result.year == 2026

    def test_naive_gets_utc(self):
        result = mod._parse_dt("2026-03-01T10:00:00")
        assert result.tzinfo == UTC


class TestCurrentFromSchedule:
    def test_schedule_not_found(self, client):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            mod._current_from_schedule("nonexistent")

    def test_returns_primary(self, client):
        client.post("/api/v1/schedules", json={
            "team": "team-a",
            "primary": ["alice", "bob"],
            "secondary": ["carol"],
            "rotation": "daily",
        })
        result = mod._current_from_schedule("team-a")
        assert result["team"] == "team-a"
        assert result["primary"] in ["alice", "bob"]
        assert result["secondary"] == "carol"
        assert "as_of" in result


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


class TestCreateSchedule:
    def test_create_basic(self, client):
        r = client.post("/api/v1/schedules", json={
            "team": "platform",
            "primary": ["alice", "bob"],
            "rotation": "weekly",
        })
        assert r.status_code == 200
        assert r.json()["team"] == "platform"

    def test_create_with_secondary(self, client):
        r = client.post("/api/v1/schedules", json={
            "team": "infra",
            "primary": ["alice"],
            "secondary": ["carol"],
            "rotation": "daily",
        })
        assert r.status_code == 200

    def test_invalid_rotation(self, client):
        r = client.post("/api/v1/schedules", json={
            "team": "x",
            "primary": ["a"],
            "rotation": "monthly",
        })
        assert r.status_code == 400

    def test_missing_primary(self, client):
        r = client.post("/api/v1/schedules", json={
            "team": "x",
            "primary": [],
            "rotation": "weekly",
        })
        assert r.status_code == 422


class TestListSchedules:
    def test_empty(self, client):
        r = client.get("/api/v1/schedules")
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_after_create(self, client):
        client.post("/api/v1/schedules", json={
            "team": "t1", "primary": ["a"], "rotation": "daily"
        })
        r = client.get("/api/v1/schedules")
        assert len(r.json()["items"]) == 1


class TestCurrentOncall:
    def test_no_schedule(self, client):
        r = client.get("/api/v1/oncall/current?team=missing")
        assert r.status_code == 404

    def test_with_schedule(self, client):
        client.post("/api/v1/schedules", json={
            "team": "team-a", "primary": ["alice"], "rotation": "weekly"
        })
        r = client.get("/api/v1/oncall/current?team=team-a")
        assert r.status_code == 200
        assert r.json()["primary"] == "alice"


class TestEscalate:
    def test_escalate_existing_team(self, client):
        client.post("/api/v1/schedules", json={
            "team": "team-b",
            "primary": ["alice"],
            "secondary": ["bob"],
            "rotation": "daily",
        })
        r = client.post("/api/v1/escalate", json={
            "team": "team-b", "incident_id": "inc-123"
        })
        assert r.status_code == 200
        assert r.json()["escalated_to"] in ["alice", "bob"]

    def test_escalate_missing_team(self, client):
        r = client.post("/api/v1/escalate", json={"team": "nope"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------

class TestReadSecret:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "env_val")
        monkeypatch.delenv("MY_VAR_FILE", raising=False)
        assert mod._read_secret("MY_VAR") == "env_val"

    def test_from_file(self, monkeypatch, tmp_path):
        f = tmp_path / "s.txt"
        f.write_text("file_val\n")
        monkeypatch.setenv("MY_VAR_FILE", str(f))
        monkeypatch.delenv("MY_VAR", raising=False)
        assert mod._read_secret("MY_VAR") == "file_val"

    def test_file_not_found_falls_back(self, monkeypatch):
        monkeypatch.setenv("MY_VAR_FILE", "/nonexistent/path")
        monkeypatch.setenv("MY_VAR", "fallback")
        assert mod._read_secret("MY_VAR") == "fallback"

    def test_default(self, monkeypatch):
        monkeypatch.delenv("NOPE", raising=False)
        monkeypatch.delenv("NOPE_FILE", raising=False)
        assert mod._read_secret("NOPE", "default") == "default"


class TestBuildDatabaseUrl:
    def test_uses_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
        monkeypatch.delenv("DATABASE_PASSWORD_FILE", raising=False)
        assert mod._build_database_url() == "sqlite:///:memory:"

    def test_replaces_password(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:old@host:5432/db")
        monkeypatch.setenv("DATABASE_PASSWORD", "newpass")
        monkeypatch.delenv("DATABASE_PASSWORD_FILE", raising=False)
        result = mod._build_database_url()
        assert "newpass" in result
        assert "old" not in result


class TestUpdateSchedule:
    def test_update_existing_schedule(self, client):
        """Creating a schedule with the same team name should update it."""
        client.post("/api/v1/schedules", json={
            "team": "update-team", "primary": ["alice"], "rotation": "weekly"
        })
        r = client.post("/api/v1/schedules", json={
            "team": "update-team", "primary": ["bob", "carol"], "rotation": "daily"
        })
        assert r.status_code == 200
        # Verify updated
        r2 = client.get("/api/v1/oncall/current?team=update-team")
        assert r2.status_code == 200
        assert r2.json()["primary"] in ["bob", "carol"]
        assert r2.json()["rotation"] == "daily"


class TestRootEndpoint:
    def test_openapi_docs(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        assert r.json()["info"]["title"] == "oncall-service"


class TestScheduleWithTimestamp:
    def test_create_with_starts_at(self, client):
        r = client.post("/api/v1/schedules", json={
            "team": "ts-team",
            "primary": ["alice"],
            "rotation": "daily",
            "starts_at": "2026-01-01T00:00:00Z",
        })
        assert r.status_code == 200

    def test_list_schedules_details(self, client):
        client.post("/api/v1/schedules", json={
            "team": "detail-team", "primary": ["alice", "bob"],
            "secondary": ["carol"], "rotation": "weekly",
        })
        r = client.get("/api/v1/schedules")
        items = r.json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["team"] == "detail-team"
        assert item["primary"] == ["alice", "bob"]
        assert item["secondary"] == ["carol"]
        assert item["rotation"] == "weekly"
        assert "starts_at" in item
