import logging
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

VALID_CHANNELS = {"mock", "email", "webhook", "slack"}


def _read_secret(env_var: str, default: str = "") -> str:
    """Read a value from env, falling back to a Docker secret file (<env_var>_FILE)."""
    file_path = os.environ.get(f"{env_var}_FILE")
    if file_path:
        try:
            return open(file_path).read().strip()
        except OSError:
            pass
    return os.environ.get(env_var, default)


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

from app.tracing import init_tracing

init_tracing(app)

ONCALL_NOTIFICATIONS_SENT_TOTAL = Counter(
    "oncall_notifications_sent_total",
    "Total on-call notifications sent (spec-required metric)",
    ["channel", "status"],
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


@app.post("/api/v1/notify", status_code=201)
async def notify(payload: NotifyIn, request: Request):
    """Send a notification."""
    request_id = getattr(request.state, "request_id", "unknown")
    channel = (payload.channel or "mock").strip().lower()

    if channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}",
        )

    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    try:
        if channel == "email":
            # Real email sending via Resend API (https://resend.com/docs/api-reference)
            api_key = _read_secret("RESEND_API_KEY")
            sender = os.environ.get("RESEND_FROM", "noreply@transcendence.games")

            if not api_key or "PLACEHOLDER" in api_key.upper():
                logger.warning(
                    "RESEND_API_KEY not configured - email logged but not sent.",
                    extra={"incident_id": payload.incident_id, "request_id": request_id},
                )
            else:
                recipients = [payload.target] if payload.target else ["devops@transcendence.games"]
                email_payload = {
                    "from": sender,
                    "to": recipients,
                    "subject": f"[IMS] Incident Alert: {payload.incident_id}",
                    "html": (
                        f"<h2>Incident Notification</h2>"
                        f"<p><strong>Incident ID:</strong> {payload.incident_id}</p>"
                        f"<p><strong>Message:</strong> {payload.message}</p>"
                        f"<p><em>Sent at {ts}</em></p>"
                    ),
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json=email_payload,
                    )
                    r.raise_for_status()
                    logger.info(
                        f"Email sent via Resend: status={r.status_code}",
                        extra={
                            "incident_id": payload.incident_id,
                            "recipients": recipients,
                            "resend_response": r.json(),
                        },
                    )

        elif channel == "webhook":
            # Webhook notification delivery
            target_url = payload.target
            if target_url and target_url.startswith("http"):
                webhook_body = {
                    "incident_id": payload.incident_id,
                    "message": payload.message,
                    "timestamp": ts,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(target_url, json=webhook_body)
                    r.raise_for_status()
                    logger.info(
                        f"Webhook delivered: status={r.status_code}",
                        extra={"incident_id": payload.incident_id, "target": target_url},
                    )
            else:
                logger.warning(
                    "Webhook channel used but no valid target URL provided - logged only.",
                    extra={"incident_id": payload.incident_id, "target": target_url},
                )

        # Log notification details (always, for all channels)
        logger.info(
            "Notification processed",
            extra={
                "channel": channel,
                "incident_id": payload.incident_id,
                "target": payload.target,
                "notification_message": payload.message[:100],
                "request_id": request_id,
                "timestamp": ts,
            },
        )

        ONCALL_NOTIFICATIONS_SENT_TOTAL.labels(channel=channel, status="sent").inc()
    except httpx.HTTPStatusError as e:
        ONCALL_NOTIFICATIONS_SENT_TOTAL.labels(channel=channel, status="failed").inc()
        logger.error(
            f"Notification delivery failed (HTTP {e.response.status_code}): {e}",
            extra={"channel": channel, "incident_id": payload.incident_id},
        )
        raise HTTPException(status_code=502, detail=f"Upstream delivery failed: {e.response.status_code}") from e
    except Exception as e:
        ONCALL_NOTIFICATIONS_SENT_TOTAL.labels(channel=channel, status="failed").inc()
        logger.error(
            f"Notification delivery failed: {e}",
            extra={"channel": channel, "incident_id": payload.incident_id},
        )
        raise HTTPException(status_code=500, detail="Notification delivery failed") from e

    return JSONResponse(
        status_code=201,
        content={"status": "sent", "channel": channel, "incident_id": payload.incident_id},
    )
