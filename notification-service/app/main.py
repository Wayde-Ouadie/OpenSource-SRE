import sys
import uuid
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("notification-service")

app = FastAPI(
    title="notification-service",
    description="Multi-channel notification delivery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

NOTIFICATIONS_SENT_TOTAL = Counter(
    "notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)

ONCALL_NOTIFICATIONS_SENT_TOTAL = Counter(
    "oncall_notifications_sent_total",
    "Total on-call notifications sent",
    ["channel"],
)


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
    return {"status": "ok", "service": "notification"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class NotifyIn(BaseModel):
    incident_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    channel: str = Field(default="mock")
    target: str | None = None


@app.post("/api/v1/notify")
def notify(payload: NotifyIn, request: Request):
    """Send a notification."""
    request_id = getattr(request.state, "request_id", "unknown")
    channel = (payload.channel or "mock").strip().lower()
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Skeleton behavior: log to stdout.
    logger.info(f"Notification sent", extra={
        "channel": channel,
        "incident_id": payload.incident_id,
        "target": payload.target,
        "notification_message": payload.message[:100],
        "request_id": request_id,
        "timestamp": ts
    })

    NOTIFICATIONS_SENT_TOTAL.labels(channel=channel, status="sent").inc()
    ONCALL_NOTIFICATIONS_SENT_TOTAL.labels(channel=channel).inc()
    return {"status": "sent", "channel": channel, "incident_id": payload.incident_id}
