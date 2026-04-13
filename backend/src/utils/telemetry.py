import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# The gRPC endpoint of your OpenTelemetry Collector.
# In Docker Compose, "otel-collector" resolves to the collector container.
# For local dev outside Docker, swap this to "http://localhost:4317".
OTEL_ENDPOINT = "http://otel-collector:4317"


def setup_telemetry(app=None, service_name: str = "save-stack-api"):
    """
    Bootstraps the three OTel signals (traces, metrics, logs) for a FastAPI app
    and registers them with the global OTel SDK providers.

    Call this once at application startup, passing in your FastAPI `app` instance.
    All signals are tagged with `service_name` so they're identifiable in
    Grafana / Tempo / Loki / Prometheus.
    """

    # Resource: metadata attached to every piece of telemetry emitted by this process.
    # SERVICE_NAME is what shows up as the service label in Grafana/Tempo/Loki.
    resource = Resource.create({SERVICE_NAME: service_name})

    # ── TRACES ────────────────────────────────────────────────────────────────
    # Traces track the lifecycle of a request across functions/services.
    # Each unit of work is a "span"; spans nest to form a "trace".

    tracer_provider = TracerProvider(resource=resource)

    # BatchSpanProcessor buffers spans in memory and flushes them in batches
    # rather than one-by-one — better for throughput in production.
    # OTLPSpanExporter sends them to the collector via gRPC.
    # insecure=True disables TLS — fine for internal Docker networking.
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        )
    )

    # Register as the global tracer provider so `trace.get_tracer(__name__)`
    # works anywhere in the codebase without passing the provider around.
    trace.set_tracer_provider(tracer_provider)

    # ── METRICS ───────────────────────────────────────────────────────────────
    # Metrics are numeric measurements over time: counters, histograms, gauges.
    # e.g. request count, latency buckets, active connections.

    # PeriodicExportingMetricReader collects all registered instruments on an
    # interval (default: 60s) and pushes them to the collector.
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    )

    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])

    # Register globally so `metrics.get_meter(__name__)` works anywhere.
    metrics.set_meter_provider(meter_provider)

    # ── LOGS ──────────────────────────────────────────────────────────────────
    # OTel logs bridge your existing logger output into the OTel pipeline,
    # letting Loki/Grafana correlate logs with the traces they belong to
    # via trace_id and span_id fields.

    logger_provider = LoggerProvider(resource=resource)

    # BatchLogRecordProcessor buffers log records and flushes in batches,
    # same philosophy as BatchSpanProcessor for traces.
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        )
    )

    # Register globally so the OTel logging bridge handler picks it up.
    set_logger_provider(logger_provider)

    # Bridge Python's standard logging module into the OTel pipeline.
    # Without this, logger.info(...) calls go to stdout only — the LoggerProvider
    # exists but nothing feeds into it. LoggingInstrumentor patches the logging
    # module so every log record is also forwarded to the OTel SDK.
    # LoggingHandler then attaches the provider to the root logger explicitly.
    LoggingInstrumentor().instrument(set_logging_format=True)
    handler = LoggingHandler(logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)

    # ── AUTO-INSTRUMENTATION ──────────────────────────────────────────────────
    # These patch FastAPI and httpx at runtime — no manual span creation needed.

    # FastAPIInstrumentor wraps every route handler in a span automatically.
    # Captures HTTP method, route, status code, and latency out of the box.
    if app is not None and not FastAPIInstrumentor().is_instrumented_by_opentelemetry:
        FastAPIInstrumentor.instrument_app(app)

    # HTTPXClientInstrumentor wraps every outgoing httpx request in a child span.
    # Critical for tracing calls to the X (Twitter) API and any other external services,
    # so they appear as child spans inside the parent request trace.
    HTTPXClientInstrumentor().instrument()


# This is your OpenTelemetry (OTel) bootstrap for the Savestack API. It sets up the three pillars of observability — traces, metrics, and logs — and ships them all to a central OTel Collector over gRPC (port 4317). It also auto-instruments FastAPI and httpx so you get spans without manual instrumentation.
# Flow:

# Creates a Resource that tags all telemetry with the service name (Savestack-api)
# Wires up a TracerProvider → batches spans → exports to collector
# Wires up a MeterProvider → periodically reads metrics → exports to collector
# Wires up a LoggerProvider → batches log records → exports to collector
# Patches FastAPI and httpx automatically so incoming requests and outgoing HTTP calls produce spans