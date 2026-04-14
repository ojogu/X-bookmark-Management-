# Bookmark Sync Architecture

## Overview

This document describes the bookmark synchronization architecture between X (Twitter) API and our database. The system uses a dual-strategy approach to keep bookmark data fresh while also ensuring historical data completeness.

### Why Two Sync Strategies?

X API does not provide a way to filter bookmarks by time (no `start_time`/`end_time` parameters). This creates a fundamental challenge:

- **Front sync**: User wants ONLY new bookmarks since last sync
- **But API returns**: All bookmarks, newest first

We solve this with two independent strategies:

| Strategy | Purpose | When to Use |
|----------|---------|-------------|
| Front Sync | Keep current with new bookmarks | Runs frequently (every 5-15 min) |
| Backfill | Catch historical data | Runs less frequently (hourly) |

---

## Architecture Components

### 1. Initial Fetch

**Trigger**: When a user first connects their X account  
**Purpose**: Bootstrap the system with recent bookmarks

```
[User OAuth complete]
         ↓
[initial_fetch_task(user_id)]
         ↓
Call API: get_bookmarks(max_results=20)
         ↓
Save to DB:
  - bookmarks
  - front_sync_token = null (no pagination yet)
  - next_token = response.next_token (for backfill)
  - is_backfill_complete = false
  - last_front_sync_time = null (will be set by first front sync)
```

**Design Decision**: Limit to 20 bookmarks (X API max per request) to minimize API credits usage. This gives us a starting point, then front sync takes over.

**Why not full sync?**
- X API rate limits (15 requests per 15 min for most apps)
- Users may have thousands of bookmarks
- Full initial sync would consume excessive API credits
- Front sync will gradually pull newer bookmarks

---

### 2. Front Sync

**Trigger**: Celery Beat cron (every 5-15 minutes)  
**Purpose**: Fetch newly saved bookmarks since last sync

```
[Celery Beat] → fetch_user_id_for_front_sync_task
         ↓
[For each user] → front_sync_bookmark_task.delay(user_id)
         ↓
┌─────────────────────────────────────────────────────┐
│ Loop:                                              │
│  1. Get front_sync_token from DB (or None)         │
│  2. Call API: get_bookmarks(                       │
│       pagination_token=front_sync_token,           │
│       max_results=20)                              │
│  3. Save bookmarks (upsert - duplicates OK)        │
│  4. response.next_token → save as front_sync_token │
│  5. If response.next_token exists →               │
│       re-queue: front_sync_bookmark_task.delay()   │
│     else → STOP                                    │
└─────────────────────────────────────────────────────┘
         ↓
Update: last_front_sync_time = now()
```

**Token Flow**:
```
User Table:
  last_front_sync_time: "2025-01-15T10:00:00Z"
  front_sync_token: "token_abc123"
  
Bookmark Table:
  front_sync_token: "token_abc123"  ← used for pagination
```

**Re-queue mechanism**: Task re-queues itself (`self.delay(user_id)`) when there's a next_token. This prevents long-running tasks and allows better error handling per page.

**Trade-off**: Why re-queue instead of loop?
- **Pro**: If one page fails, we don't lose progress on previous pages
- **Pro**: Better observability - each page is a separate task
- **Con**: More task overhead (more Celery messages)
- **Alternative**: Loop internally - faster but riskier on failure

---

### 3. Backfill

**Trigger**: Celery Beat cron (every 15-60 minutes)  
**Purpose**: Fetch historical bookmarks that were missed or not yet synced

```
[Celery Beat] → fetch_user_id_for_backfill_task
         ↓
[For each user] → backfill_bookmark_task.delay(user_id)
         ↓
┌─────────────────────────────────────────────────────┐
│ Loop:                                              │
│  1. Get next_token from DB (or None)               │
│  2. Call API: get_bookmarks(                       │
│       pagination_token=next_token,                │
│       max_results=20)                              │
│  3. If no results →                               │
│       set is_backfill_complete = true             │
│       STOP                                         │
│  4. Save bookmarks                                 │
│  5. response.next_token → save as next_token     │
│  6. If response.next_token exists →               │
│       re-queue: backfill_bookmark_task.delay()    │
│     else →                                        │
│       set is_backfill_complete = true             │
│       STOP                                         │
└─────────────────────────────────────────────────────┘
```

**Token Flow**:
```
User Table:
  is_backfill_complete: false
  
Bookmark Table:
  next_token: "token_xyz789"  ← used for pagination
```

**Completion detection**: When `response.next_token` is empty AND no bookmarks returned, mark `is_backfill_complete = true` to stop future backfill runs for this user.

---

## Data Model

### User Table Fields

| Field | Type | Purpose |
|-------|------|---------|
| `last_front_sync_time` | DateTime | Timestamp of last successful front sync |
| `is_backfill_complete` | Boolean | Flag to skip backfill when done |

### Bookmark Table Fields

| Field | Type | Purpose |
|-------|------|---------|
| `front_sync_token` | String | Pagination token for front sync |
| `next_token` | String | Pagination token for backfill |
| `is_backfill_complete` | Boolean | Per-user flag (actually on User table) |

**Important**: Both tokens are stored per-bookmark but effectively represent the user's global pagination state. All bookmarks for a user share the same token values.

---

## Rate Limiting

### X API Limits (varies by app tier)

- **Tier 1**: 15 requests per 15 minutes
- **Tier 1.5**: 100 requests per 15 minutes  
- **Tier 2**: 1000 requests per 15 minutes

### Implementation Strategy

Using `tenacity` library in `twitter.py`:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((
        httpx.ConnectError,
        httpx.RequestError,
        httpx.TimeoutException,
        ExternalAPIError  # includes 429 handling
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def get_bookmarks(...):
    ...
```

**For 429 (Too Many Requests)**:
- Exponential backoff: wait 2s, 4s, 8s... up to 60s
- After 3 attempts, raise exception (task will retry later via Celery)
- Log warning before each retry

**Trade-off**: Task-based retries vs. internal retries
- Current: Each API call has internal retry (3 attempts)
- Alternative: Fail immediately, let Celery re-queue task
- **Decision**: Internal retry is simpler for now; can evolve if 429 is frequent

---

## Upsert Mechanism

The system uses upsert (update or insert) to handle overlapping data:

1. **No time filtering needed**: We don't filter by `created_at >= last_sync_time`
2. **Duplicates are OK**: If a bookmark already exists, the upsert is idempotent
3. **Race conditions**: Celery tasks run sequentially per user (via queue), reducing conflicts

**How upsert works** in `BookmarkService.save_bookmarks()`:

```python
# Check if exists
existing_bm = await self.check_if_bookmark_exists(db, post_id, user_id)

if not existing_bm:
    # Create new
    bookmark = BookmarkModel(...)
    db.add(bookmark)
# If exists → do nothing (already in DB)
```

---

## Task Queue Configuration

### Celery Queues

| Queue | Purpose | Routing Key |
|-------|---------|-------------|
| `default` | General tasks | `default` |
| `fetch_user_id_for_front_sync_task` | Cron trigger | `fetch_user_id_for_front_sync_task` |
| `front_sync_bookmark_task` | Front sync worker | `front_sync_bookmark_task` |
| `fetch_user_id_for_backfill_task` | Cron trigger | `fetch_user_id_for_backfill_task` |
| `backfill_bookmark_task` | Backfill worker | `backfill_bookmark_task` |

### Celery Beat Schedule (Proposed)

```python
beat_schedule = {
    'front-sync-every-5-minutes': {
        'task': 'src.celery.task.fetch_user_id_for_front_sync_task',
        'schedule': 300.0,  # 5 minutes
    },
    'backfill-every-15-minutes': {
        'task': 'src.celery.task.fetch_user_id_for_backfill_task',
        'schedule': 900.0,  # 15 minutes
    },
}
```

---

## Trade-offs Summary

| Decision | Trade-off |
|----------|------------|
| Two sync strategies (front + backfill) | More complex, but solves X API limitations |
| Re-queue instead of loop | More Celery overhead, but better failure isolation |
| Upsert vs. time filter | Wastes API credits on old data, but simpler code |
| 20 bookmarks per request | More API calls, but respects rate limits |
| Internal retry + Celery retry | Double retry, but higher reliability |

---

## Future Improvements

1. **WebSocket push**: Notify frontend when sync completes
2. **Staleness indicator**: Show "Last synced: X min ago" in UI
3. **Tier-based scheduling**: Adjust frequency based on user activity
4. **Token persistence**: Consider storing next_token per-bookmark for granular recovery
5. **Front sync optimization**: If `last_front_sync_time` is very old, warn user or limit sync window