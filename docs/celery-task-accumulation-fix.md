# Celery Task Accumulation Bug - Root Cause Analysis & Fix

**Date:** April 2026  
**Status:** Resolved  
**Author:** Engineering Team

---

## Problem Statement

On April 14th, the sync system experienced a severe traffic spike causing:

- Read operations: 30 → 400 in a short window
- Task queue backup
- X API rate limit violations
- Worker instability

The immediate assumption was "lost tasks" or "RabbitMQ requeuing issues" — but the root cause was **uncontrolled task accumulation due to missing `max_retries` on Celery tasks**.

---

## Root Cause Analysis

### What Happened

```
Worker picks up task → Task fails with unexpected error → No max_retries → Retry infinitely → Queue backup
```

### The Failure Chain

```
1. Task starts executing
2. Hits a bug (not ConnectionError/TimeoutError)
3. Raises exception
4. Tenacity doesn't catch it (only configured for ConnectionError/TimeoutError)
5. Exception propagates to Celery
6. Celery requeues the task (no max_retries set)
7. Repeat all night → backlog accumulates
8. Bug gets fixed
9. All accumulated tasks flush at once → API spike
```

### Why Tenacity Wasn't the Problem

Tenacity was correctly configured:
- Retries only on `ConnectionError` and `TimeoutError`
- Max 3 attempts
- Exponential backoff

The actual bug was a **different exception type** that tenacity wasn't configured to retry. When tenacity let it pass through, Celery's default behavior kicked in — and **Celery had no `max_retries` set**, causing infinite retries.

### Key Insight

> Without `max_retries` on `@shared_task`, Celery retries **forever** on any unhandled exception. This is the default behavior when using `self.retry()` without bounds.

---

## Solution Implemented

### 1. Added Max Retries to Celery Tasks

```python
@shared_task(bind=True, max_retries=3)  # ← Critical addition
def front_sync_bookmark_task(self, user_id):
    ...
```

**Effect:** Tasks now fail permanently after 3 attempts, preventing infinite accumulation.

### 2. Replaced Tenacity with Celery Native Retry

**Before:**
```python
@shared_task(bind=True)
@retry(
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
)
def front_sync_bookmark_task(self, user_id):
    ...
```

**After:**
```python
@shared_task(bind=True, max_retries=3, 
             autoretry_for=(ConnectionError, TimeoutError),
             retry_backoff=True,
             retry_backoff_max=600)
def front_sync_bookmark_task(self, user_id):
    ...
```

**Rationale:**
- Celery's built-in retry integrates with task state tracking
- Simpler configuration (no decorator layering)
- Single source of truth for retry behavior

### 3. Added Per-User Rate Limiting

**Problem:** Even with `max_retries`, a wave of re-queued tasks could still overwhelm the system.

**Solution:** Redis-based per-user rate limiting at task entry:

```python
RATE_LIMIT = 5          # Max concurrent tasks per user
RATE_LIMIT_WINDOW = 60  # Window in seconds
RATE_LIMIT_RETRY_DELAY = 180  # Delay before retry when blocked

def is_rate_limited(user_id: str) -> bool:
    r = get_redis_sync()
    key = f"rate_limit:sync:{user_id}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, RATE_LIMIT_WINDOW)
    return current > RATE_LIMIT
```

**Usage in task:**
```python
@shared_task(bind=True, max_retries=3)
def front_sync_bookmark_task(self, user_id):
    if is_rate_limited(str(user_id)):
        raise self.retry(countdown=RATE_LIMIT_RETRY_DELAY)
    ...
```

**Effect:** Even if 100 tasks re-queue for a user at once, only 5 run immediately. The rest wait 3 minutes and retry, preventing API spikes.

---

## Tradeoffs & Considerations

### Max Retries Tradeoffs

| Pros | Cons |
|------|------|
| Prevents infinite accumulation | Failed tasks need manual re-run from DLQ |
| Predictable failure behavior | Must monitor DLQ for stuck tasks |
| Cleaner debugging (finite retries) | May need to adjust based on X API reliability |

**Recommendation:** Monitor dead letter queue and set up alerts for tasks that exceed max retries.

### Rate Limiting Tradeoffs

| Pros | Cons |
|------|------|
| Prevents burst spikes | Adds latency for rate-limited tasks |
| Per-user isolation | Requires Redis (already in stack) |
| Self-healing (auto-retry) | 3-minute delay may be too long/short |

**Alternative Considered:** Celery's built-in rate limiting (`task_annotations`) — but it limits globally, not per-user. Redis-based approach is more flexible.

### Tenacity Removal Tradeoffs

| Pros | Cons |
|------|------|
| Single retry mechanism (Celery) | Lose fine-grained tenacity features |
| Simpler code | Must configure retry in one place |
| Better integration with Celery | Less flexible for complex retry logic |

**Note:** Tenacity is still used elsewhere in the codebase for API call retries (Twitter service, OAuth), just not in Celery tasks.

---

## Monitoring Recommendations

1. **Set up alerts for:**
   - Tasks exceeding max retries (goes to DLQ)
   - Rate-limited task count per hour
   - Queue depth spikes

2. **Dashboards to add:**
   - Task retry count distribution
   - Rate limit hit frequency
   - DLQ size over time

3. **Runbook for spike response:**
   - Check if bug was recently fixed
   - Review DLQ for pattern
   - Consider draining accumulated tasks gradually

---

## Files Changed

| File | Change |
|------|--------|
| `src/celery/task.py` | Added max_retries, rate limiting, removed tenacity |
| `src/utils/redis.py` | Added sync Redis client for Celery |
| `src/celery/celery_config.py` | Already had `task_max_retries = 3` |

---

## Conclusion

The bug was **not** lost messages or RabbitMQ issues — it was **unbounded Celery retries** without a `max_retries` cap. The fix combines:

1. **max_retries=3** — Prevents infinite accumulation
2. **Per-user rate limiting** — Prevents burst spikes
3. **Celery native retry** — Simpler, integrated retry behavior

Together, these ensure that even when bugs cause failures, the system self-limits and doesn't create cascading API spikes.