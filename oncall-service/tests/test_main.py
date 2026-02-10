"""Tests for oncall-service helper functions and API endpoints."""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import SCHEDULES, _current_from_schedule, _escalated_incidents, _parse_dt, app


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("INCIDENT_MGMT_BASE_URL", "http://fake:8002")
    monkeypatch.setenv("NOTIFICATION_BASE_URL", "http://fake:8004")


@pytest.fixture()
def client():
    SCHEDULES.clear()
    _escalated_incidents.clear()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_none_returns_now(self):
        result = _parse_dt(None)
        assert result.tzinfo is not None

    def test_zulu(self):
        result = _parse_dt("2026-01-15T12:00:00Z")
        assert result.year == 2026

    def test_iso(self):
        result = _parse_dt("2026-01-15T12:00:00+00:00")
        assert result.year == 2026

    def test_naive_gets_utc(self):
        result = _parse_dt("2026-03-01T10:00:00")
        assert result.tzinfo == UTC


class TestCurrentFromSchedule:
    def test_schedule_not_found(self):
        SCHEDULES.clear()
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _current_from_schedule("nonexistent")

    def test_returns_primary(self):
        SCHEDULES.clear()
        SCHEDULES["team-a"] = {
            "primary": ["alice", "bob"],
            "secondary": ["carol"],
            "rotation": "daily",
            "starts_at": datetime.now(UTC),
        }
        result = _current_from_schedule("team-a")
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
