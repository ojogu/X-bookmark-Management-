# Celery Worker OOM Incident & Resolution

**Date:** 2026-04-14  
**Status:** Resolved  
**Severity:** High  

---

## 1. Problem Summary

The Celery worker container was crashing with `SIGKILL` (signal 9) immediately after startup, preventing background task processing.

### Symptoms

```
worker-1 | 2026-04-14 11:51:36,004 INFO [celery.apps.worker] celery@133e6d18b539 ready.
worker-1 | [2026-04-14 11:51:36,005] [ERROR] multiprocessing - Process 'ForkPoolWorker-1' pid:21 exited with 'signal 9 (SIGKILL)'
worker-1 | CRITICAL [celery.worker] - Unrecoverable error: WorkerLostError('Could not start worker processes')
```

### Impact

- All background tasks (bookmark sync, backfill) were halted
- User data not syncing to external APIs
- Scheduled cron jobs not executing

---

## 2. Root Cause Analysis

### Primary Cause: Memory Exhaustion (OOM)

Signal 9 (`SIGKILL`) is sent by the Linux kernel's Out-of-Memory (OOM) killer when a process exceeds available memory limits.

### Contributing Factors

| Factor | Details |
|--------|---------|
| **Container Memory Limit** | Worker container limited to 512MB |
| **Celery Pool Type** | Default `prefork` pool forks multiple Python processes |
| **Default Concurrency** | Celery defaults to `number of CPU cores` forked processes |
| **Task Memory Usage** | Background tasks load large libraries and data |

### Why Prefork?

- **Prefork pool** creates separate Python processes using `multiprocessing`
- Each forked process inherits the parent's memory (copy-on-write)
- With default concurrency (4+), this quickly exhausts 512MB
- Container's memory limit (`deploy.resources.limits.memory`) enforces hard limit

### Technical Flow

```
Container starts with 512MB limit
  ↓
Celery forks 4+ worker processes (default concurrency)
  ↓
Each process inherits memory from parent
  ↓
Total memory usage exceeds 512MB
  ↓
OOM Killer sends SIGKILL to offending process
  ↓
Celery worker crashes
```

---

## 3. Solution Applied

### Part A: Memory & Concurrency Fix

### Changes in `docker-compose.yml`

```yaml
worker:
  # BEFORE
  deploy:
    resources:
      limits:
        memory: 512m    # ❌ Too low for prefork pool

  # AFTER
  deploy:
    resources:
      limits:
        memory: 1G     # ✅ Doubled for multiple processes
      reservations:
        memory: 512M
  environment:
    - CELERYD_CONCURRENCY=2  # ✅ Explicit concurrency limit
```

```yaml
celery-beat:
  # BEFORE
  deploy:
    resources:
      limits:
        memory: 256m
  
  # AFTER (minor increase)
  deploy:
    resources:
      limits:
        memory: 512M   # ✅ More headroom for scheduler
```

### Configuration Summary

| Setting | Before | After |
|---------|--------|-------|
| Worker Memory | 512MB | 1GB |
| Worker Reservation | 256MB | 512MB |
| Concurrency | Default (CPU cores) | 2 |
| Beat Memory | 256MB | 512MB |

---

### Part B: Queue Listening Fix

### The Problem

Tasks were showing as "pending" in Flower but never executing. The worker wasn't consuming from the correct queues.

### Root Cause

By default, Celery only listens to the `default` queue. However, the system is configured with multiple queues:

- `default` - general tasks
- `fetch_user_id_for_front_sync_task` - cron job trigger
- `front_sync_bookmark_task` - bookmark sync
- `fetch_user_id_for_backfill_task` - backfill cron trigger
- `backfill_bookmark_task` - backfill tasks

The `task_routes` in `celery_config.py` routes tasks to specific queues, but the worker needs explicit permission to consume from them.

### Solution

Add the `-Q` flag to the worker command in `docker-compose.yml`:

```yaml
# BEFORE
command: celery -A src.celery.celery worker -l info

# AFTER
command: celery -A src.celery.celery worker -l info -Q default,fetch_user_id_for_front_sync_task,front_sync_bookmark_task,fetch_user_id_for_backfill_task,backfill_bookmark_task
```

### What `-Q` Does

- `-Q` specifies which queues the worker should consume from
- The worker will pull tasks from all listed queues
- `task_routes` still controls which queue each task type goes to

### Alternative: Use `task_queues` Config

Instead of specifying `-Q` on command line, you could set:

```python
worker_default_queue = "default"
task_queues = (
    Queue("default", routing_key="default"),
    # ... other queues
)
```

And start worker without `-Q` - it will consume all queues defined in config.

We chose explicit `-Q` for clarity and to avoid accidentally consuming queues not intended for this worker.

---

## 4. Tradeoffs & Considerations

### Tradeoffs

| Tradeoff | Impact | Mitigation |
|----------|--------|------------|
| **Higher Memory Usage** | More container RAM needed | Monitor actual usage, adjust if needed |
| **Lower Concurrency** | Fewer parallel tasks | 2 is sufficient for current workload |
| **More Container Resources** | Higher hosting costs | Scaling is proportional to workload |

### What We Kept

- **Prefork pool** - Retained for multi-process benefits:
  - True parallelism for CPU-bound tasks
  - Process isolation (one crash doesn't affect others)
  - Better for heavy computation

### Why Not Solo Pool?

Solo pool would have solved OOM but was not chosen because:

- No parallelism (single task at a time)
- All tasks in same process (risk of memory leaks)
- Not suitable for production workloads

### Future Considerations

1. **Monitor actual usage**
   ```bash
   docker stats savestack_worker_1
   ```

2. **Scale workers horizontally**
   - Run multiple worker containers
   - Add `--hostname` for distinct names

3. **Add resource monitoring**
   - Set up alerts for memory > 80%
   - Track in Grafana dashboards

4. **Consider gevent for I/O-bound tasks**
   - Lower memory, higher concurrency
   - Good for API calls

---

## 5. Verification

### Check Worker Status

```bash
# View worker logs
docker-compose logs worker

# Check worker is running
docker-compose ps

# Access Flower monitoring
open http://localhost:5555
```

### Expected Behavior

- Worker starts without OOM errors
- Logs show: `celery@... ready`
- Flower shows 2 concurrent workers

---

## 6. Related Configuration

### Celery Config (`src/celery/celery_config.py`)

```python
class CeleryConfig:
    worker_prefetch_multiplier = 1    # Conservative prefetch
    task_acks_late = True             # Acknowledge after completion
    worker_max_tasks_per_child = 1000  # Recycle processes
```

### Docker Resource Syntax

```yaml
deploy:
  resources:
    limits:
      memory: 1G      # Hard limit (container killed if exceeded)
    reservations:
      memory: 512M    # Guaranteed allocation
```

---

## 7. References

- [Celery Workers](https://docs.celeryq.dev/en/stable/userguide/workers.html)
- [Docker Compose Resources](https://docs.docker.com/compose/compose-file/deploy/#resources)
- [Linux OOM Killer](https://www.kernel.org/doc/Documentation/admin-guide/mm/concepts.rst)

---

*Last updated: 2026-04-14*