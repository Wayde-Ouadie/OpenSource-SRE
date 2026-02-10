import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, Text, create_engine, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _read_secret(env_var: str, default: str = "") -> str:
    """Read a value from env, falling back to a Docker secret file (<env_var>_FILE)."""
    file_path = os.environ.get(f"{env_var}_FILE")
    if file_path:
        try:
            return open(file_path).read().strip()
        except OSError:
            pass
    return os.environ.get(env_var, default)


def _build_database_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://opensource:placeholder@postgres:5432/incident_management",
    )
    secret_pw = _read_secret("DATABASE_PASSWORD")
    if secret_pw:
        # Replace the password segment in the URL  (user:password@host)
        import re
        url = re.sub(r"(://[^:]+:)[^@]+(@)", rf"\g<1>{secret_pw}\2", url)
    return url


DATABASE_URL = _build_database_url()
ONCALL_BASE_URL = os.environ.get("ONCALL_BASE_URL", "http://oncall-service:8003")
NOTIFICATION_BASE_URL = os.environ.get("NOTIFICATION_BASE_URL", "http://notification-service:8004")

# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "service", "incident_id", "action"):
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JSONFormatter())
logger = logging.getLogger("incident-management")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(_handler)
logger.propagate = False

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = {"schema": "incident_management"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, default=list)
    timeline: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
INCIDENTS_TOTAL = Counter("incidents_total", "Total incidents by status", ["status"])
INCIDENT_MTTA = Histogram(
    "incident_mtta_seconds", "Mean time to acknowledge (seconds)",
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)
INCIDENT_MTTR = Histogram(
    "incident_mttr_seconds", "Mean time to resolve (seconds)",
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800],
)
INCIDENTS_OPEN = Gauge("incidents_open", "Currently open incidents", ["severity"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def _append_timeline(incident: "Incident", event_type: str, detail: str, actor: str = "system") -> None:
    """Append a timestamped event to the incident timeline."""
    entry = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "detail": detail,
        "actor": actor,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    current = list(incident.timeline or [])
    current.append(entry)
    incident.timeline = current


def _calculate_metrics(incident: Incident) -> dict[str, float | None]:
    mtta = mttr = None
    if incident.acknowledged_at:
        mtta = (incident.acknowledged_at - incident.created_at).total_seconds()
    if incident.resolved_at:
        mttr = (incident.resolved_at - incident.created_at).total_seconds()
    return {"mtta_seconds": mtta, "mttr_seconds": mttr}


def _create_http_client() -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(timeout=httpx.Timeout(5.0), transport=transport)


async def _lookup_oncall_and_notify(service: str, incident_id: str, title: str) -> str | None:
    """Call on-call service to find current engineer, then send notification."""
    assigned_to = None
    try:
        async with _create_http_client() as client:
            # On-call lookup
            r = await client.get(f"{ONCALL_BASE_URL}/api/v1/oncall/current", params={"team": service})
            if r.status_code == 200:
                data = r.json()
                assigned_to = data.get("primary")
                logger.info(f"On-call lookup: {assigned_to}", extra={"incident_id": incident_id, "service": service})

            # Send notification
            await client.post(
                f"{NOTIFICATION_BASE_URL}/api/v1/notify",
                json={
                    "incident_id": incident_id,
                    "message": f"New incident: {title}",
                    "channel": "mock",
                    "target": assigned_to,
                },
            )
    except Exception as e:
        logger.warning(f"Cross-service call failed: {e}", extra={"incident_id": incident_id})
    return assigned_to


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class IncidentCreate(BaseModel):
    service: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    extra_data: dict[str, Any] | None = None


class IncidentUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    description: str | None = None


class NoteIn(BaseModel):
    content: str = Field(min_length=1)
    author: str = Field(default="system")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database schema and tables (if not exist)")
    if "sqlite" not in DATABASE_URL:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("CREATE SCHEMA IF NOT EXISTS incident_management"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
    logger.info("Incident-management service ready")
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="incident-management-service",
    description="Core incident lifecycle management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from app.tracing import init_tracing

init_tracing(app)

app.add_middleware(RequestIDMiddleware)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "incident-management"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/incidents")
async def create_incident(payload: IncidentCreate):
    """Create a new incident. Auto-assigns via on-call lookup and sends notification."""
    severity = payload.severity.strip().lower()
    if severity not in VALID_SEVERITIES:
        severity = "medium"

    incident = Incident(
        service=payload.service.strip(),
        severity=severity,
        title=payload.title.strip(),
        description=payload.description,
        status="open",
        extra_data=payload.extra_data,
        notes=[],
        timeline=[],
    )

    with SessionLocal() as session:
        session.add(incident)
        _append_timeline(incident, "created", f"Incident created with severity '{severity}'")
        session.commit()
        session.refresh(incident)
        incident_id = str(incident.id)

    INCIDENTS_TOTAL.labels(status="open").inc()
    INCIDENTS_OPEN.labels(severity=severity).inc()

    # Cross-service: on-call lookup + notification (non-blocking best-effort)
    assigned = await _lookup_oncall_and_notify(
        incident.service, incident_id, incident.title,
    )
    if assigned:
        with SessionLocal() as session:
            inc = session.get(Incident, incident.id)
            if inc and not inc.assigned_to:
                inc.assigned_to = assigned
                session.commit()

    return {
        "id": incident_id,
        "service": incident.service,
        "severity": incident.severity,
        "title": incident.title,
        "status": incident.status,
        "assigned_to": assigned,
        "created_at": _fmt_dt(incident.created_at),
    }


@app.get("/api/v1/incidents")
async def list_incidents(
    status: str | None = Query(None),
    service: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List incidents with optional filters."""
    with SessionLocal() as session:
        stmt = select(Incident)
        if status:
            stmt = stmt.where(Incident.status == status.strip().lower())
        if service:
            stmt = stmt.where(Incident.service == service.strip())
        if severity:
            stmt = stmt.where(Incident.severity == severity.strip().lower())
        stmt = stmt.order_by(Incident.created_at.desc()).limit(limit)
        incidents = session.execute(stmt).scalars().all()

        return {
            "items": [
                {
                    "id": str(inc.id),
                    "service": inc.service,
                    "severity": inc.severity,
                    "title": inc.title,
                    "status": inc.status,
                    "assigned_to": inc.assigned_to,
                    "created_at": _fmt_dt(inc.created_at),
                    "acknowledged_at": _fmt_dt(inc.acknowledged_at),
                    "resolved_at": _fmt_dt(inc.resolved_at),
                }
                for inc in incidents
            ],
            "count": len(incidents),
        }


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident by ID."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="invalid_incident_id") from err

    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")

        m = _calculate_metrics(incident)

        return {
            "id": str(incident.id),
            "service": incident.service,
            "severity": incident.severity,
            "title": incident.title,
            "description": incident.description,
            "status": incident.status,
            "assigned_to": incident.assigned_to,
            "extra_data": incident.extra_data,
            "notes": incident.notes or [],
            "timeline": incident.timeline or [],
            "created_at": _fmt_dt(incident.created_at),
            "acknowledged_at": _fmt_dt(incident.acknowledged_at),
            "resolved_at": _fmt_dt(incident.resolved_at),
            "mtta_seconds": m["mtta_seconds"],
            "mttr_seconds": m["mttr_seconds"],
        }


@app.get("/api/v1/incidents/{incident_id}/metrics")
async def get_incident_metrics(incident_id: str):
    """Get MTTA/MTTR metrics for a specific incident."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="invalid_incident_id") from err

    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")

        m = _calculate_metrics(incident)
        return {
            "incident_id": str(incident.id),
            "mtta_seconds": m["mtta_seconds"],
            "mttr_seconds": m["mttr_seconds"],
            "status": incident.status,
            "created_at": _fmt_dt(incident.created_at),
            "acknowledged_at": _fmt_dt(incident.acknowledged_at),
            "resolved_at": _fmt_dt(incident.resolved_at),
        }


@app.patch("/api/v1/incidents/{incident_id}")
async def update_incident(incident_id: str, payload: IncidentUpdate):
    """Update incident status or assignment."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="invalid_incident_id") from err

    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")

        old_status = incident.status

        if payload.status:
            new_status = payload.status.strip().lower()
            if new_status in {"open", "acknowledged", "in_progress", "resolved"}:
                incident.status = new_status

                if new_status == "acknowledged" and not incident.acknowledged_at:
                    incident.acknowledged_at = datetime.now(UTC)
                    _created = incident.created_at.replace(tzinfo=UTC) if incident.created_at.tzinfo is None else incident.created_at
                    mtta = (incident.acknowledged_at - _created).total_seconds()
                    INCIDENT_MTTA.observe(mtta)

                if new_status == "resolved" and not incident.resolved_at:
                    incident.resolved_at = datetime.now(UTC)
                    _created = incident.created_at.replace(tzinfo=UTC) if incident.created_at.tzinfo is None else incident.created_at
                    mttr = (incident.resolved_at - _created).total_seconds()
                    INCIDENT_MTTR.observe(mttr)
                    INCIDENTS_OPEN.labels(severity=incident.severity).dec()

                if old_status != new_status:
                    INCIDENTS_TOTAL.labels(status=new_status).inc()
                    _append_timeline(incident, "status_change", f"Status changed from '{old_status}' to '{new_status}'")

        if payload.assigned_to is not None:
            old_assignee = incident.assigned_to
            incident.assigned_to = payload.assigned_to.strip() if payload.assigned_to else None
            if old_assignee != incident.assigned_to:
                _append_timeline(incident, "assignment", f"Assigned to '{incident.assigned_to}' (was '{old_assignee or 'unassigned'}')")

        if payload.description is not None:
            incident.description = payload.description

        session.commit()
        session.refresh(incident)

        return {
            "id": str(incident.id),
            "status": incident.status,
            "assigned_to": incident.assigned_to,
        }


@app.post("/api/v1/incidents/{incident_id}/notes")
async def add_note(incident_id: str, payload: NoteIn):
    """Add a note/comment to an incident."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="invalid_incident_id") from err

    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")

        note = {
            "id": str(uuid.uuid4()),
            "content": payload.content,
            "author": payload.author,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

        current_notes = list(incident.notes or [])
        current_notes.append(note)
        incident.notes = current_notes

        _append_timeline(incident, "note_added", f"Note added by {payload.author}")

        session.commit()

        return {"status": "ok", "note": note}


@app.get("/")
def root():
    return {"service": "incident-management", "version": "1.0.0"}
