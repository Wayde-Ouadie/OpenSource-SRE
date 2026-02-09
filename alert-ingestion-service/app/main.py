import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
import logging

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from sqlalchemy import JSON, DateTime, String, create_engine, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("alert-ingestion")

app = FastAPI(
    title="alert-ingestion-service",
    description="Receives and correlates alerts into incidents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

INCIDENT_MGMT_BASE_URL = os.environ.get("INCIDENT_MGMT_BASE_URL", "http://incident-management:8002")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management",
)


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


def _init_models() -> None:
    Base.metadata.create_all(bind=engine)


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


def _normalize_severity(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"critical", "high", "medium", "low"}:
        return v
    if v in {"warn", "warning"}:
        return "medium"
    if v in {"error"}:
        return "high"
    return "low"


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        # Accepts ISO8601 like 2026-03-08T15:30:00Z
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


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


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    """Health check endpoint."""
    logger.info("Health check requested")
    return {"status": "ok", "service": "alert-ingestion"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/alerts", response_model=AlertOut)
async def create_alert(payload: AlertIn, request: Request):
    """Create a new alert and correlate it to an incident."""
    _init_models()
    
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Received alert", extra={
        "service": payload.service,
        "severity": payload.severity,
        "request_id": request_id
    })

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

    # Correlate: same service + severity within 5 minutes, status=open.
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    try:
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            transport=transport
        ) as client:
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
        # Keep skeleton resilient: store alert even if IM is down.
        logger.warning(f"Failed to contact incident-management: {str(e)}", extra={"request_id": request_id})
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
    
    logger.info(f"Alert processed", extra={
        "alert_id": str(alert.id),
        "incident_id": incident_id,
        "action": action,
        "request_id": request_id
    })

    return AlertOut(
        alert_id=str(alert.id),
        incident_id=incident_id,
        status=status,
        action=action,
    )


@app.get("/api/v1/alerts/{alert_id}")
def get_alert(alert_id: str):
    _init_models()
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
