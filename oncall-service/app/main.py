import time
import sys
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("oncall-service")

app = FastAPI(
    title="oncall-service",
    description="On-call schedule and escalation management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

SCHEDULES: dict[str, dict[str, Any]] = {}

ONCALL_CURRENT = Gauge(
    "oncall_current",
    "Current on-call engineer (1 means active)",
    ["team", "engineer", "role"],
)

ESCALATIONS_TOTAL = Counter(
    "escalations_total",
    "Total escalations",
    ["team"],
)


class ScheduleIn(BaseModel):
    team: str = Field(min_length=1)
    primary: list[str] = Field(min_length=1, description="Rotation list for primary")
    secondary: list[str] | None = Field(default=None, description="Rotation list for secondary")
    rotation: str = Field(default="weekly", description="weekly|daily")
    starts_at: str | None = Field(default=None, description="ISO8601; defaults to now")


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _current_from_schedule(team: str) -> dict[str, Any]:
    schedule = SCHEDULES.get(team)
    if not schedule:
        raise HTTPException(status_code=404, detail="schedule_not_found")

    start = schedule["starts_at"]
    rotation = schedule["rotation"]
    primary = schedule["primary"]
    secondary = schedule.get("secondary") or []

    now = datetime.now(timezone.utc)
    seconds = max(0, (now - start).total_seconds())
    period = 86400 if rotation == "daily" else 7 * 86400
    idx = int(seconds // period) % max(1, len(primary))

    primary_engineer = primary[idx % len(primary)]
    secondary_engineer = secondary[idx % len(secondary)] if secondary else None

    # Update gauge: clear previous for this team.
    ONCALL_CURRENT.clear()
    ONCALL_CURRENT.labels(team=team, engineer=primary_engineer, role="primary").set(1)
    if secondary_engineer:
        ONCALL_CURRENT.labels(team=team, engineer=secondary_engineer, role="secondary").set(1)

    return {
        "team": team,
        "primary": primary_engineer,
        "secondary": secondary_engineer,
        "rotation": rotation,
        "as_of": now.isoformat().replace("+00:00", "Z"),
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    logger.info("Health check requested")
    return {"status": "ok", "service": "oncall"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/schedules")
def list_schedules():
    return {
        "items": [
            {
                "team": team,
                "primary": sched["primary"],
                "secondary": sched.get("secondary"),
                "rotation": sched["rotation"],
                "starts_at": sched["starts_at"].isoformat().replace("+00:00", "Z"),
            }
            for team, sched in SCHEDULES.items()
        ]
    }


@app.post("/api/v1/schedules")
def create_schedule(payload: ScheduleIn, request: Request):
    """Create or update an on-call schedule."""
    request_id = getattr(request.state, "request_id", "unknown")
    team = payload.team.strip()
    if not team:
        raise HTTPException(status_code=400, detail="invalid_team")
    rotation = payload.rotation.strip().lower()
    if rotation not in {"weekly", "daily"}:
        raise HTTPException(status_code=400, detail="invalid_rotation")

    SCHEDULES[team] = {
        "primary": [x.strip() for x in payload.primary if x.strip()],
        "secondary": [x.strip() for x in (payload.secondary or []) if x.strip()],
        "rotation": rotation,
        "starts_at": _parse_dt(payload.starts_at),
        "created_at": time.time(),
    }
    
    logger.info(f"Created schedule for team", extra={"team": team, "rotation": rotation, "request_id": request_id})

    return {"status": "ok", "team": team}


@app.get("/api/v1/oncall/current")
def current_oncall(team: str = Query(min_length=1)):
    """Get current on-call engineer for a team."""
    logger.info(f"Getting current on-call for team", extra={"team": team})
    return _current_from_schedule(team.strip())


class EscalateIn(BaseModel):
    team: str = Field(min_length=1)
    incident_id: str | None = None


@app.post("/api/v1/escalate")
def escalate(payload: EscalateIn, request: Request):
    """Escalate an incident to secondary on-call."""
    request_id = getattr(request.state, "request_id", "unknown")
    team = payload.team.strip()
    ESCALATIONS_TOTAL.labels(team=team).inc()
    current = _current_from_schedule(team)
    
    logger.info(f"Escalated for team", extra={
        "team": team,
        "incident_id": payload.incident_id,
        "escalated_to": current.get("secondary") or current.get("primary"),
        "request_id": request_id
    })
    
    return {"status": "ok", "team": team, "escalated_to": current.get("secondary") or current.get("primary")}
