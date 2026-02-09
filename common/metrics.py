"""Common Prometheus metrics."""
from prometheus_client import Counter, Histogram, Gauge


# HTTP Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

# Service health
service_up = Gauge(
    "service_up",
    "Service health status (1 = up, 0 = down)",
    ["service"]
)
