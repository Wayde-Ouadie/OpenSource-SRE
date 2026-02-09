import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, generate_latest
from sqlalchemy import JSON, DateTime, String, Text, create_engine, select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

app = FastAPI(
    title="incident-management-service",
    description="Core incident lifecycle management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management",
)

# Prometheus Metrics
INCIDENTS_TOTAL = Counter(
    "incidents_total",
    "Total incidents by status",
    ["status"],
)

INCIDENT_MTTA = Histogram(
    "incident_mtta_seconds",
    "Mean time to acknowledge (seconds)",
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)

INCIDENT_MTTR = Histogram(
    "incident_mttr_seconds",
    "Mean time to resolve (seconds)",
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800],
)

INCIDENTS_OPEN = Gauge(
    "incidents_open",
    "Currently open incidents",
    ["severity"],
)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _init_models() -> None:
    Base.metadata.create_all(bind=engine)


def _calculate_metrics(incident: Incident) -> dict[str, float | None]:
    """Calculate MTTA and MTTR for an incident."""
    mtta = None
    mttr = None
    
    if incident.acknowledged_at:
        mtta = (incident.acknowledged_at - incident.created_at).total_seconds()
    
    if incident.resolved_at:
        mttr = (incident.resolved_at - incident.created_at).total_seconds()
    
    return {"mtta": mtta, "mttr": mttr}


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


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "incident-management"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/incidents")
async def create_incident(payload: IncidentCreate):
    """Create a new incident."""
    _init_models()
    
    severity = payload.severity.strip().lower()
    if severity not in {"critical", "high", "medium", "low"}:
        severity = "medium"
    
    incident = Incident(
        service=payload.service.strip(),
        severity=severity,
        title=payload.title.strip(),
        description=payload.description,
        status="open",
        extra_data=payload.extra_data,
    )
    
    with SessionLocal() as session:
        session.add(incident)
        session.commit()
        session.refresh(incident)
        
        INCIDENTS_TOTAL.labels(status="open").inc()
        INCIDENTS_OPEN.labels(severity=severity).inc()
        
        return {
            "id": str(incident.id),
            "service": incident.service,
            "severity": incident.severity,
            "title": incident.title,
            "status": incident.status,
            "created_at": incident.created_at.isoformat().replace("+00:00", "Z"),
        }


@app.get("/api/v1/incidents")
async def list_incidents(
    status: str | None = Query(None),
    service: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List incidents with optional filters."""
    _init_models()
    
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
                    "created_at": inc.created_at.isoformat().replace("+00:00", "Z"),
                    "acknowledged_at": inc.acknowledged_at.isoformat().replace("+00:00", "Z") if inc.acknowledged_at else None,
                    "resolved_at": inc.resolved_at.isoformat().replace("+00:00", "Z") if inc.resolved_at else None,
                }
                for inc in incidents
            ],
            "count": len(incidents),
        }


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident by ID."""
    _init_models()
    
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_incident_id")
    
    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")
        
        metrics = _calculate_metrics(incident)
        
        return {
            "id": str(incident.id),
            "service": incident.service,
            "severity": incident.severity,
            "title": incident.title,
            "description": incident.description,
            "status": incident.status,
            "assigned_to": incident.assigned_to,
            "extra_data": incident.extra_data,
            "created_at": incident.created_at.isoformat().replace("+00:00", "Z"),
            "acknowledged_at": incident.acknowledged_at.isoformat().replace("+00:00", "Z") if incident.acknowledged_at else None,
            "resolved_at": incident.resolved_at.isoformat().replace("+00:00", "Z") if incident.resolved_at else None,
            "mtta_seconds": metrics["mtta"],
            "mttr_seconds": metrics["mttr"],
        }


@app.patch("/api/v1/incidents/{incident_id}")
async def update_incident(incident_id: str, payload: IncidentUpdate):
    """Update incident status or assignment."""
    _init_models()
    
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_incident_id")
    
    with SessionLocal() as session:
        incident = session.get(Incident, incident_uuid)
        if not incident:
            raise HTTPException(status_code=404, detail="incident_not_found")
        
        old_status = incident.status
        
        if payload.status:
            new_status = payload.status.strip().lower()
            if new_status in {"open", "acknowledged", "in_progress", "resolved"}:
                incident.status = new_status
                
                # Update timestamps based on status transitions
                if new_status == "acknowledged" and not incident.acknowledged_at:
                    incident.acknowledged_at = datetime.now(timezone.utc)
                    mtta = (incident.acknowledged_at - incident.created_at).total_seconds()
                    INCIDENT_MTTA.observe(mtta)
                
                if new_status == "resolved" and not incident.resolved_at:
                    incident.resolved_at = datetime.now(timezone.utc)
                    mttr = (incident.resolved_at - incident.created_at).total_seconds()
                    INCIDENT_MTTR.observe(mttr)
                    INCIDENTS_OPEN.labels(severity=incident.severity).dec()
                
                # Update counters
                if old_status != new_status:
                    INCIDENTS_TOTAL.labels(status=new_status).inc()
        
        if payload.assigned_to is not None:
            incident.assigned_to = payload.assigned_to.strip() if payload.assigned_to else None
        
        if payload.description is not None:
            incident.description = payload.description
        
        session.commit()
        session.refresh(incident)
        
        return {
            "id": str(incident.id),
            "status": incident.status,
            "assigned_to": incident.assigned_to,
        }


@app.get("/")
def root():
    """Root endpoint."""
    return {"service": "incident-management", "version": "1.0.0"}
