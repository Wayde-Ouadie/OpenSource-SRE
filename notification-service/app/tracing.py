"""OpenTelemetry tracing bootstrap – graceful no-op when unconfigured."""
import os, logging

logger = logging.getLogger(__name__)

def init_tracing(app=None):
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    service  = os.environ.get("OTEL_SERVICE_NAME", "unknown")
    if not endpoint:
        logger.info("OTEL endpoint not set – tracing disabled")
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider = TracerProvider(resource=Resource.create({"service.name": service}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
        trace.set_tracer_provider(provider)
        if app:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)
            except Exception: pass
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception: pass
        logger.info(f"Tracing enabled → {endpoint} as '{service}'")
    except ImportError as e:
        logger.warning(f"OTel packages missing – tracing disabled: {e}")
    except Exception as e:
        logger.error(f"Tracing init failed: {e}")
