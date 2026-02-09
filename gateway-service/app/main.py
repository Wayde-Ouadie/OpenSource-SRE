import os
import sys
import uuid
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("gateway-service")

INCIDENT_MGMT_BASE_URL = os.environ.get("INCIDENT_MGMT_BASE_URL", "http://incident-management:8002")

app = FastAPI(
    title="gateway-service",
    description="API Gateway for routing requests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
    return {"status": "ok", "service": "gateway"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/health")
async def api_health(request: Request):
    """Proxy health check to incident management."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Proxying health check", extra={"request_id": request_id})
    
    try:
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            transport=transport
        ) as client:
            r = await client.get(f"{INCIDENT_MGMT_BASE_URL}/health")
            return r.json()
    except Exception as e:
        logger.error(f"Health check failed", extra={"error": str(e), "request_id": request_id})
        return {"status": "error", "message": str(e)}
