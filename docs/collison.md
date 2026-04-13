# Engineering Doc: OTel Provider Collision Between Celery Worker and FastAPI Backend

**Project:** SaveStack  
**Date:** April 2026

---

## The Issue

After wiring up the full OTel pipeline (traces, metrics, logs → Collector → Loki/Prometheus/Tempo), the FastAPI backend (`save-stack-api`) was not appearing in Loki. Only the Celery worker (`savestack-worker`) was showing up.

The backend container logs showed these warnings on every startup:

```
Overriding of current TracerProvider is not allowed
Overriding of current MeterProvider is not allowed
Overriding of current LoggerProvider is not allowed
```

And all OTel providers were tagged with `resource.service.name=savestack-worker` — inside the backend process.

---

## Root Cause

The Celery app is defined in `src/celery/celery.py`. At the bottom of that file, `setup_telemetry(service_name="savestack-worker")` was called at **module level**:

```python
# src/celery/celery.py
bg_task = Celery("src", ...)

setup_telemetry(service_name="savestack-worker")  # runs on import
CeleryInstrumentor().instrument()
```

The FastAPI backend imports Celery tasks at some point during startup, which causes Python to import `src.celery.celery`. The moment that module is imported, `setup_telemetry("savestack-worker")` runs and registers the worker's OTel providers globally.

By the time `main.py` calls `setup_telemetry(service_name="save-stack-api")`, the providers are already locked — the OTel SDK does not allow overriding registered providers. So the backend ends up using the worker's providers, and all its telemetry is either dropped or tagged incorrectly.

---

## The Fix

### 1. Guard the Celery telemetry behind an environment variable

In `src/celery/celery.py`, wrap the telemetry setup so it only runs when the process is actually a Celery worker — not when the module is imported by FastAPI:

```python
import os

# ── OpenTelemetry ─────────────────────────────────────────────────
# Guard ensures this only runs in actual worker/beat processes.
# Without this, importing this module in FastAPI triggers worker
# telemetry setup and locks the global OTel providers before the
# API can register its own.
if os.getenv("CELERY_WORKER") == "true":
    setup_telemetry(service_name="savestack-worker")
    CeleryInstrumentor().instrument()
# ─────────────────────────────────────────────────────────────────
```

### 2. Set the environment variable on worker containers only

In `docker-compose.yml`, add `CELERY_WORKER=true` to the `worker` and `celery-beat` services — but NOT the backend:

```yaml
worker:
  environment:
    - CELERY_WORKER=true

celery-beat:
  environment:
    - CELERY_WORKER=true
```

The backend service has no `CELERY_WORKER` variable, so the guard evaluates to false and the worker telemetry never runs inside the API process.

---

## Result

After the fix:

- Backend startup no longer shows provider override warnings
- `save-stack-api` appears as a distinct service in Loki's label browser
- `savestack-worker` continues to appear separately
- Each service's logs, traces, and metrics are correctly isolated under their own `service.name`

---

## Key Takeaway

OTel providers are **global singletons** — once registered, they cannot be overridden in the same process. Any module that calls `setup_telemetry()` at import time will claim the providers for the entire process. Always guard environment-specific telemetry setup behind a runtime condition, never run it unconditionally at module level in shared code.