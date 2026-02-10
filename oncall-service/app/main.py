import os
import sys
import uuid
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INCIDENT_MGMT_BASE_URL = os.environ.get("INCIDENT_MGMT_BASE_URL", "http://incident-management:8002")
NOTIFICATION_BASE_URL = os.environ.get("NOTIFICATION_BASE_URL", "http://notification-service:8004")
ESCALATION_THRESHOLD_MINUTES = int(os.environ.get("ESCALATION_THRESHOLD_MINUTES", "5"))
ESCALATION_CHECK_INTERVAL = int(os.environ.get("ESCALATION_CHECK_INTERVAL", "60"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger("oncall-service")

# ---------------------------------------------------------------------------
# In-memory data
# ---------------------------------------------------------------------------
SCHEDULES: dict[str, dict[str, Any]] = {}
# Track incidents we already escalated so we don't repeat
_escalated_incidents: set[str] = set()

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class ScheduleIn(BaseModel):
    team: str = Field(min_length=1)
    primary: list[str] = Field(min_length=1, description="Rotation list for primary")
    secondary: list[str] | None = Field(default=None, description="Rotation list for secondary")
    rotation: str = Field(default="weekly", description="weekly|daily")
    starts_at: str | None = Field(default=None, description="ISO8601; defaults to now")


class EscalateIn(BaseModel):
    team: str = Field(min_length=1)
    incident_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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


# ---------------------------------------------------------------------------
# Background: Timed Auto-Escalation
# ---------------------------------------------------------------------------
async def _escalation_loop():
    """Periodically check for unacknowledged incidents older than threshold
    and auto-escalate them to the secondary on-call engineer."""
    logger.info(
        f"Auto-escalation loop started "
        f"(threshold={ESCALATION_THRESHOLD_MINUTES}min, interval={ESCALATION_CHECK_INTERVAL}s)"
    )

    while True:
        await asyncio.sleep(ESCALATION_CHECK_INTERVAL)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                # Get open incidents that haven't been acknowledged
                r = await client.get(
                    f"{INCIDENT_MGMT_BASE_URL}/api/v1/incidents",
                    params={"status": "open", "limit": 50},
                )
                if r.status_code != 200:
                    continue

                data = r.json()
                now = datetime.now(timezone.utc)
                threshold = timedelta(minutes=ESCALATION_THRESHOLD_MINUTES)

                for inc in data.get("items", []):
                    inc_id = inc.get("id", "")
                    # Skip if already escalated or already acknowledged
                    if inc_id in _escalated_incidents:
                        continue
                    if inc.get("acknowledged_at"):
                        continue

                    created_at = _parse_dt(inc.get("created_at"))
                    if (now - created_at) < threshold:
                        continue

                    # This incident has been open and unacknowledged past threshold
                    service = inc.get("service", "unknown")
                    logger.info(
                        f"Auto-escalating incident {inc_id} for service {service} "
                        f"(unacknowledged for >{ESCALATION_THRESHOLD_MINUTES}min)"
                    )

                    # Find secondary on-call for this service/team
                    escalated_to = None
                    if service in SCHEDULES:
                        try:
                            current = _current_from_schedule(service)
                            escalated_to = current.get("secondary") or current.get("primary")
                        except Exception:
                            escalated_to = None

                    ESCALATIONS_TOTAL.labels(team=service).inc()
                    _escalated_incidents.add(inc_id)

                    # Assign incident to secondary via PATCH
                    if escalated_to:
                        try:
                            await client.patch(
                                f"{INCIDENT_MGMT_BASE_URL}/api/v1/incidents/{inc_id}",
                                json={"assigned_to": escalated_to},
                            )
                        except Exception as e:
                            logger.warning(f"Failed to reassign incident {inc_id}: {e}")

                    # Send escalation notification
                    try:
                        await client.post(
                            f"{NOTIFICATION_BASE_URL}/api/v1/notify",
                            json={
                                "incident_id": inc_id,
                                "message": f"ESCALATION: Incident {inc_id} unacknowledged >{ESCALATION_THRESHOLD_MINUTES}min, escalating to {escalated_to or 'manager'}",
                                "channel": "mock",
                                "target": escalated_to,
                            },
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send escalation notification for {inc_id}: {e}")

        except Exception as e:
            logger.error(f"Escalation loop error: {e}")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("On-call service starting")
    task = asyncio.create_task(_escalation_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="oncall-service",
    description="On-call schedule and escalation management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from app.tracing import init_tracing
init_tracing(app)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
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

    logger.info(f"Created schedule for team {team}", extra={"team": team, "rotation": rotation, "request_id": request_id})

    return {"status": "ok", "team": team}


@app.get("/api/v1/oncall/current")
def current_oncall(team: str = Query(min_length=1)):
    """Get current on-call engineer for a team."""
    logger.info(f"Getting current on-call for team {team}")
    return _current_from_schedule(team.strip())


@app.post("/api/v1/escalate")
def escalate(payload: EscalateIn, request: Request):
    """Manually escalate an incident to secondary on-call."""
    request_id = getattr(request.state, "request_id", "unknown")
    team = payload.team.strip()
    ESCALATIONS_TOTAL.labels(team=team).inc()
    current = _current_from_schedule(team)

    logger.info(f"Escalated for team {team}", extra={
        "team": team,
        "incident_id": payload.incident_id,
        "escalated_to": current.get("secondary") or current.get("primary"),
        "request_id": request_id,
    })

    return {"status": "ok", "team": team, "escalated_to": current.get("secondary") or current.get("primary")}
