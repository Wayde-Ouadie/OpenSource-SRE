import time

from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


INCIDENTS_TOTAL = Counter(
    "incidents_total",
    "Total incidents by status transition",
    ["status"],
)

INCIDENT_MTTA_SECONDS = Histogram(
    "incident_mtta_seconds",
    "Incident mean time to acknowledge (seconds)",
)

INCIDENT_MTTR_SECONDS = Histogram(
    "incident_mttr_seconds",
    "Incident mean time to resolve (seconds)",
)


class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start

        path = getattr(request, "path", "unknown")
        method = getattr(request, "method", "unknown")
        status_code = getattr(response, "status_code", 0)

        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()

        return response
