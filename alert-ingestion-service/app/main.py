import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any
import logging
import json

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from sqlalchemy import JSON, DateTime, String, create_engine, select
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
        "postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management",
    )
    secret_pw = _read_secret("DATABASE_PASSWORD")
    if secret_pw:
        import re
        url = re.sub(r"(://[^:]+:)[^@]+(@)", rf"\g<1>{secret_pw}\2", url)
    return url


INCIDENT_MGMT_BASE_URL = os.environ.get(
    "INCIDENT_MGMT_BASE_URL", "http://incident-management:8002"
)
DATABASE_URL = _build_database_url()

# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via `extra={…}`
        for key in ("request_id", "service", "severity", "alert_id", "incident_id", "action"):
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JSONFormatter())
logger = logging.getLogger("alert-ingestion")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(_handler)
logger.propagate = False

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    labels: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
ALERTS_RECEIVED_TOTAL = Counter(
    "alerts_received_total",
    "Total alerts received",
    ["severity"],
)

ALERTS_CORRELATED_TOTAL = Counter(
    "alerts_correlated_total",
    "Total alert correlation outcomes",
    ["result"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
SEVERITY_ALIASES = {"warn": "medium", "warning": "medium", "error": "high"}


def _normalize_severity(value: str) -> str:
    v = (value or "").strip().lower()
    if v in VALID_SEVERITIES:
        return v
    return SEVERITY_ALIASES.get(v, "low")


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _create_http_client() -> httpx.AsyncClient:
    """Create a resilient async HTTP client with retries."""
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(timeout=httpx.Timeout(5.0), transport=transport)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class AlertIn(BaseModel):
    service: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    message: str = Field(min_length=1)
    labels: dict[str, Any] | None = None
    timestamp: str | None = None


class AlertOut(BaseModel):
    alert_id: str
    incident_id: str | None
    status: str
    action: str


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID to every request & response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Lifespan — run table creation once at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables (if not exist)")
    Base.metadata.create_all(bind=engine)
    logger.info("Alert-ingestion service ready")
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="alert-ingestion-service",
    description="Receives and correlates alerts into incidents",
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
    """Health check endpoint."""
    return {"status": "ok", "service": "alert-ingestion"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/alerts", response_model=AlertOut)
async def create_alert(payload: AlertIn, request: Request):
    """Receive, validate, normalize, and correlate an alert into an incident."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "Received alert",
        extra={"service": payload.service, "severity": payload.severity, "request_id": request_id},
    )

    severity = _normalize_severity(payload.severity)
    ALERTS_RECEIVED_TOTAL.labels(severity=severity).inc()

    alert = Alert(
        service=payload.service.strip(),
        severity=severity,
        message=payload.message.strip(),
        labels=payload.labels,
        timestamp=_parse_timestamp(payload.timestamp),
    )

    incident_id: str | None = None
    action = "created_new_incident"
    status = "correlated"

    # Correlation: same service + severity within 5 minutes, status=open
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    try:
        async with _create_http_client() as client:
            r = await client.get(
                f"{INCIDENT_MGMT_BASE_URL}/api/v1/incidents",
                params={"status": "open", "service": alert.service, "severity": alert.severity},
            )
            r.raise_for_status()
            items = (r.json() or {}).get("items") or []
            for incident in items:
                created_at = incident.get("created_at")
                if created_at and isinstance(created_at, str):
                    dt = _parse_timestamp(created_at)
                    if dt >= cutoff:
                        incident_id = incident.get("id")
                        action = "attached_to_existing_incident"
                        break

            if incident_id is None:
                r2 = await client.post(
                    f"{INCIDENT_MGMT_BASE_URL}/api/v1/incidents",
                    json={"service": alert.service, "severity": alert.severity, "title": alert.message},
                )
                r2.raise_for_status()
                incident_id = (r2.json() or {}).get("id")
    except Exception as e:
        # Keep service resilient: store alert even if incident-management is down
        logger.warning(
            f"Failed to contact incident-management: {e}",
            extra={"request_id": request_id},
        )
        status = "accepted"
        action = "stored_only"

    if incident_id:
        alert.incident_id = str(incident_id)
        if action == "attached_to_existing_incident":
            ALERTS_CORRELATED_TOTAL.labels(result="existing_incident").inc()
        else:
            ALERTS_CORRELATED_TOTAL.labels(result="new_incident").inc()
    else:
        ALERTS_CORRELATED_TOTAL.labels(result="new_incident").inc()

    with SessionLocal() as session:
        session.add(alert)
        session.commit()
        session.refresh(alert)

    logger.info(
        "Alert processed",
        extra={
            "alert_id": str(alert.id),
            "incident_id": incident_id,
            "action": action,
            "request_id": request_id,
        },
    )

    return AlertOut(
        alert_id=str(alert.id),
        incident_id=incident_id,
        status=status,
        action=action,
    )


@app.get("/api/v1/alerts/{alert_id}")
def get_alert(alert_id: str):
    """Retrieve a single alert by ID."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_alert_id")

    with SessionLocal() as session:
        alert = session.get(Alert, alert_uuid)
        if alert is None:
            raise HTTPException(status_code=404, detail="not_found")
        return {
            "alert_id": str(alert.id),
            "service": alert.service,
            "severity": alert.severity,
            "message": alert.message,
            "labels": alert.labels,
            "timestamp": alert.timestamp.isoformat().replace("+00:00", "Z"),
            "incident_id": alert.incident_id,
        }


@app.get("/", response_class=PlainTextResponse)
def root():
    return "alert-ingestion-service"
