# OTel → Loki Log Pipeline: Debugging Journal

**Project:** SaveStack API  
**Stack:** FastAPI · structlog · OpenTelemetry SDK · OTel Collector · Loki 3.0 · Grafana  
**Date:** March 2026

---

## The Goal

Ship application logs from the FastAPI backend through the OpenTelemetry Collector into Loki, so they're queryable in Grafana alongside traces (Tempo) and metrics (Prometheus).

The pipeline:

```
FastAPI app (structlog)
       ↓
  OTel SDK (LoggerProvider)
       ↓
  OTel Collector (otlphttp/loki exporter)
       ↓
      Loki
       ↓
    Grafana
```

---

## Issue 1: `setup_telemetry()` was never called

### Symptom
Loki label browser showed no labels at all. The OTel Collector logs showed only startup messages — no incoming log records.

### Root Cause
The `setup_telemetry()` function existed and was correctly written, but was never invoked in `main.py`. Without it, the OTel `LoggerProvider` was never registered, and no logs were shipped anywhere.

### Fix
Call `setup_telemetry()` once at module level in `main.py`, before routers are registered:

```python
# main.py
from src.utils.telemetry import setup_telemetry

app = FastAPI(lifespan=life_span)

setup_telemetry(app=app, service_name="save-stack-api")
```

---

## Issue 2: Loki version didn't support the OTLP endpoint

### Symptom
After fixing Issue 1, the OTel Collector started receiving logs but immediately dropped them with:

```
error exporting items, request to http://loki:3100/otlp/v1/logs
responded with HTTP Status Code 404
```

### Root Cause
The OTLP ingestion endpoint (`/otlp/v1/logs`) was introduced in **Loki 3.0**. The running version was **Loki 2.9.4**, which doesn't have it.

### Fix
Upgrade Loki to 3.0+ in `docker-compose.yml`:

```yaml
loki:
  image: grafana/loki:3.0.0
```

Then pull and restart:

```bash
docker compose pull loki
docker compose up -d loki
```

---

## Issue 3: structlog wiped the OTel logging handler

### Symptom
After fixing Issues 1 and 2, the OTel Collector confirmed log records were arriving from the Celery worker (`savestack-worker`) but not from the FastAPI API (`save-stack-api`). The API was running fine — it just wasn't sending logs.

### Root Cause
Two things combined to cause this:

**1. The logging bridge was never connected.**  
`setup_telemetry()` registered the OTel `LoggerProvider` globally and added a `LoggingHandler` to the root logger. But the app uses **structlog**, not Python's standard `logging` module directly. Without explicitly bridging structlog's output into the OTel handler, log records never reached the OTel pipeline.

**2. `configure_structlog()` cleared all handlers.**  
`configure_structlog()` runs inside the FastAPI lifespan (at startup), *after* `setup_telemetry()` runs at module level. It contained:

```python
root_logger.handlers.clear()  # this wiped the OTel handler
```

This removed the `LoggingHandler` that `setup_telemetry()` had just added, before any logs could flow through it.

### Fix

**In `telemetry.py`** — add the logging bridge inside `setup_telemetry()`:

```python
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# After set_logger_provider(logger_provider):
LoggingInstrumentor().instrument(set_logging_format=True)
handler = LoggingHandler(logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)
```

**In `log.py`** — re-add the OTel handler explicitly after `handlers.clear()`:

```python
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry._logs import get_logger_provider

def configure_structlog() -> None:
    # ... existing setup ...

    otel_handler = LoggingHandler(logger_provider=get_logger_provider())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()         # clears previous handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(otel_handler) # explicitly re-add OTel handler

    root_logger.setLevel(logging.DEBUG if is_dev else logging.INFO)
```

`get_logger_provider()` returns the already-registered provider from `setup_telemetry()`, so no state is lost — the handler is just re-wired after the clear.

---

## Final Verification

After all three fixes, the OTel Collector logs showed clean, error-free log record batches:

```
info  Logs  {"otelcol.component.id": "debug", "otelcol.signal": "logs", "log records": 13}
info  Logs  {"otelcol.component.id": "debug", "otelcol.signal": "logs", "log records": 2}
```

In Grafana → Explore → Loki, both services appeared in the label browser:

```logql
{service_name="save-stack-api"}
{service_name="savestack-worker"}
```

---

## Summary

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | No logs reaching collector | `setup_telemetry()` never called | Call it in `main.py` at module level |
| 2 | 404 on Loki OTLP endpoint | Loki 2.9.4 doesn't support OTLP | Upgrade to Loki 3.0+ |
| 3 | API logs missing, worker logs present | `handlers.clear()` wiped OTel handler; structlog not bridged to OTel | Re-add `LoggingHandler` after clear; add `LoggingInstrumentor` bridge in `setup_telemetry()` |