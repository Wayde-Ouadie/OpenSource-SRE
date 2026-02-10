import collections
import logging
import os
import sys
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("gateway-service")

INCIDENT_MGMT_BASE_URL = os.environ.get("INCIDENT_MGMT_BASE_URL", "http://incident-management:8002")

# ---------------------------------------------------------------------------
# Rate Limiter (in-memory, sliding-window per IP)
# ---------------------------------------------------------------------------
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))  # seconds

_request_log: dict[str, list[float]] = collections.defaultdict(list)


def _is_rate_limited(client_ip: str) -> bool:
    """Return True if the client has exceeded the rate limit."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    # Prune old entries
    _request_log[client_ip] = [t for t in _request_log[client_ip] if t > window_start]
    if len(_request_log[client_ip]) >= RATE_LIMIT_REQUESTS:
        return True
    _request_log[client_ip].append(now)
    return False


# ---------------------------------------------------------------------------
# API Key auth (optional — set GATEWAY_API_KEY to enable)
# ---------------------------------------------------------------------------
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
GATEWAY_REQUESTS_TOTAL = Counter(
    "gateway_requests_total",
    "Total requests through the gateway",
    ["method", "path", "status"],
)
GATEWAY_REQUEST_DURATION = Histogram(
    "gateway_request_duration_seconds",
    "Gateway request duration",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="gateway-service",
    description="API Gateway — rate limiting, auth, request logging, routing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """Combined middleware: request ID, logging, auth, rate limiting, metrics."""
    start = time.time()

    # --- Request ID ---
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    # --- Rate limiting ---
    if _is_rate_limited(client_ip):
        logger.warning(
            "Rate limited",
            extra={"client_ip": client_ip, "request_id": request_id, "path": path},
        )
        GATEWAY_REQUESTS_TOTAL.labels(method=method, path=path, status="429").inc()
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"X-Request-ID": request_id, "Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    # --- API Key auth (if configured) ---
    if GATEWAY_API_KEY and path.startswith("/api/"):
        provided = request.headers.get("X-API-Key", "")
        if provided != GATEWAY_API_KEY:
            logger.warning(
                "Unauthorized request",
                extra={"client_ip": client_ip, "request_id": request_id, "path": path},
            )
            GATEWAY_REQUESTS_TOTAL.labels(method=method, path=path, status="401").inc()
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
                headers={"X-Request-ID": request_id},
            )

    # --- Request logging ---
    logger.info(
        f"{method} {path}",
        extra={"client_ip": client_ip, "request_id": request_id},
    )

    response = await call_next(request)

    # --- Response enrichment ---
    duration = time.time() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.4f}s"

    status_code = str(response.status_code)
    GATEWAY_REQUESTS_TOTAL.labels(method=method, path=path, status=status_code).inc()
    GATEWAY_REQUEST_DURATION.labels(method=method, path=path).observe(duration)

    logger.info(
        f"{method} {path} -> {status_code} ({duration:.3f}s)",
        extra={"client_ip": client_ip, "request_id": request_id, "duration": duration},
    )

    return response


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "gateway"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/health")
async def api_health(request: Request):
    """Proxy health check to incident management."""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            transport=transport
        ) as client:
            r = await client.get(f"{INCIDENT_MGMT_BASE_URL}/health")
            return r.json()
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e), "request_id": request_id})
        return {"status": "error", "message": str(e)}
