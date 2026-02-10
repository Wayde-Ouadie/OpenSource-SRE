"""
Shared OpenTelemetry tracing bootstrap.

Usage in any FastAPI service:
    from tracing import init_tracing
    init_tracing(app)

Requires env vars (set in docker-compose):
    OTEL_SERVICE_NAME          – e.g. "alert-ingestion-service"
    OTEL_EXPORTER_OTLP_ENDPOINT – e.g. "http://jaeger:4317"
"""
import os
import logging

logger = logging.getLogger(__name__)


def init_tracing(app=None):
    """Initialise OpenTelemetry tracing.

    Gracefully no-ops if OTEL endpoint is not configured or if
    the required packages are not installed.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name = os.environ.get("OTEL_SERVICE_NAME", "unknown-service")

    if not endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set – tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)
            except Exception as e:
                logger.warning(f"FastAPI auto-instrumentation failed: {e}")

        # Auto-instrument httpx
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"httpx auto-instrumentation failed: {e}")

        logger.info(f"Tracing enabled → {endpoint} as '{service_name}'")

    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed – tracing disabled: {e}")
    except Exception as e:
        logger.error(f"Tracing init failed: {e}")
