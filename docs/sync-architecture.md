# Sync Architecture: Optimistic UI with Background Processing

## Problem Statement

### The Blocking Issue

Original `/bookmarks` endpoint:

```
GET /bookmarks → DB empty? → fetch from X API → save to DB → read back → return
                            ↑ NETWORK SLOW ↑ ↑ BLOCKING USER ↑
```

**Problems:**
- Network latency: User waits 500ms-5s
- Rate limiting: User gets error
- X API down: User sees error
- Double-read: Write then immediate read-back

---

## Solution: Optimistic UI

| Before | After |
|--------|-------|
| Inline blocking on X API | Background processing |
| Slow first load | Fast response |
| Error on X failure | Always returns data |

**Core principle:** Return immediately with what you have. Do expensive work in background.

---

## Three Sync Types

| Type | Trigger | Frequency |
|------|---------|-----------|
| Initial | First `/bookmarks` (DB empty) | Once per user |
| Front | Celery cron | Every 5 min |
| Backfill | Celery cron | Every 15 min |

---

## Implementation

**.env:** `CELERY_BEAT_INTERVAL=5`

**schemas/bookmark.py:** Add `last_synced_at` to `Meta`

**route/bookmark.py:** 
- If `count > 0` → return from DB
- If `count == 0` → return pending + trigger background task

---

## Trade-offs

| Gained | Sacrificed |
|--------|------------|
| Fast response | Stale data possible |
| No blocking | Two requests for first load |
| Reliability | More complexity (Celery) |
| Scalability | |

**Why acceptable:** Polling solves staleness, `/client/sync` for manual refresh.

---

## Future Improvements

1. **WebSocket push**: Notify frontend when sync completes
2. **Staleness indicator**: Show "Last synced: X min ago" in UI
3. **Incremental initial sync**: Don't fetch all at once