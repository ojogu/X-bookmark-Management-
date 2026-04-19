# Bookmark Sync Engineering

## Problem Statement

### The Bug

In v1 of the sync architecture, we used `front_sync_token` to track pagination for front sync:

```
front_sync_bookmark_task:
  1. Fetch bookmarks (using front_sync_token)
  2. Save bookmarks
  3. Store API's next_token as front_sync_token
  4. If next_token exists → re-queue
```

**The fatal flaw**: The X API's `next_token` always points to **older bookmarks** (paginating backward). Each run fetched older content:

| Run | Tokens | Result |
|-----|--------|--------|
| 1 | `front_sync_token=NULL` | Fetch [A,B,C,D] (newest) → store next_token=F |
| 2 | `front_sync_token=F` | Fetch [E,F,G,H] → older! |
| 3 | `front_sync_token=H` | Fetch [I,J,K,L] → even older! |

**Result**: Each front sync run went backward through history, never catching new bookmarks.

### Why No Timestamp Filter?

X API's `/get_bookmarks` endpoint **does not support** `start_time` or `end_time` parameters. These only work with the Search API, not Bookmarks.

### The Gap

```
X bookmarks: A, B, C, D, E, F, G, H, I, J... (newest → oldest)

Buggy runs:
  Run 1: Fetched A, B → stored next_token pointing to C
  Run 2: Started from next_token → fetched F, G... (SKIPPED C, D, E!)
```

**C, D, E were lost** - the next_token jumped past them.

---

## Solution: Dual-State Architecture

### Core Insight

We need **two separate concepts**:
1. **Front sync** - Always fetches newest, stops at boundary
2. **Backfill** - Uses pagination token to fill historical gaps

### New State Model

| Field | Purpose | Set By |
|-------|---------|--------|
| `front_watermark_id` | ID of newest bookmark seen | Front sync |
| `next_token` (backfill_cursor) | Pagination token for backfill | Front sync (first run only) |

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONT SYNC (runs frequently, fetches newest)                      │
├─────────────────────────────────────────────────────────────────┤
│ State: front_watermark_id                                    │
│                                                          │
│ ON EACH RUN:                                              │
│  1. Fetch max_results=2 (no pagination token)             │
│  2. IF front_watermark_id IS NULL (cold start):            │
│      - Save all bookmarks                               │
│      - front_watermark_id = newest post_id              │
│      - next_token = API's next_token  ← BACKFILL USES   │
│      - STOP                                           │
│  3. IF front_watermark_id IS SET (subsequent):          │
│      - Bulk-check post_ids against DB                  │
│      - Walk: hit existing → STOP, else collect new      │
│      - Save new bookmarks                            │
│      - front_watermark_id = newest post_id           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                     Stores next_token
                              ↓
┌───────────────────────────────────────────────────────────���─────┐
│ BACKFILL (runs independently, fills historical)              │
├─────────────────────────────────────────────────────────────────┤
│ State: next_token (backfill_cursor)                       │
│                                                          │
│ ON EACH RUN:                                              │
│  1. IF next_token IS NULL: do nothing (not cold start)    │
│  2. Fetch using next_token as pagination_token       │
│  3. Upsert bookmarks (insert new, update existing)   │
│  4. Update next_token from response              │
│  5. If no next_token → backfill complete          │
└─────────────────────────────────────────────────────────────────┘
```

### Recovery Flow (One-Time)

```
After code deploys with fix:

First Front Sync Run:
  - Fetch [A,B] (newest)
  - Save [A,B]
  - front_watermark_id = A
  - next_token = token_for_C  ← Backfill uses this!

First Backfill Run:
  - Read next_token (points to C)
  - Fetch [C,D] → upsert (recovers C, D!)
  - Fetch [E,F] → upsert (recovers E, F!)
  - Continue until no next_token
  - Done
```

---

## Implementation Details

### Database Schema

```sql
-- User table
ALTER TABLE users ADD COLUMN front_watermark_id VARCHAR(50);

-- Existing columns (retained for backfill)
next_token: VARCHAR(50);  -- used by backfill worker
is_backfill_complete: BOOLEAN;
last_front_sync_time: TIMESTAMP;
```

### Code Structure

**BookmarkService helpers**:
```python
async def fetch_front_watermark_id(db, user_id) -> str:
    """Get watermark for cold start detection."""

async def update_front_watermark_id(db, user_id, watermark_id):
    """Store newest bookmark ID."""

async def update_backfill_cursor(db, user_id, cursor):
    """Store next_token for backfill worker."""

async def get_existing_post_ids(db, user_id, post_ids) -> set:
    """Bulk-check which bookmarks exist in DB."""
```

### Front Sync Algorithm (Pseudocode)

```python
def front_sync_bookmark_task(user_id):
    # Check cold start
    watermark = fetch_front_watermark_id(user_id)
    is_cold_start = (watermark is None)

    # Fetch newest bookmarks (no pagination token)
    response = x_api.get_bookmarks(max_results=2)
    bookmarks = response.data

    if is_cold_start:
        # Cold start: save all, store state
        save_bookmarks(bookmarks)
        update_front_watermark_id(bookmarks[0].id)
        update_backfill_cursor(response.next_token)
        return

    # Subsequent: check against DB
    existing = get_existing_post_ids(post_ids)

    for bookmark in bookmarks:
        if bookmark.id in existing:
            break  # boundary reached
        collect new

    if new_bookmarks:
        save_bookmarks(new_bookmarks)
        update_front_watermark_id(new_bookmarks[0].id)
```

---

## Trade-offs

| Decision | Trade-off | Rationale |
|----------|----------|-----------|
| max_results=2 | More API calls, but safer | X API rate limit handling |
| Bulk-check vs. loop | Single DB query per page | Efficient for small pages |
| Upsert in backfill | Extra writes, but idempotent | No need to deduplicate |
| First run stores next_token | One-time credit waste | Enables backfill to continue |
| Separate front + backfill | More complex | Required due to API limitations |

### Why Not Filter by Timestamp?

X API does not support time filtering for bookmarks. The boundary-check approach (Option 1) is the only viable solution.

### Why max_results=2?

Originally set to 2 for safety with X API rate limits. Could increase to 20 if needed, but keeping conservative for now.

---

## Gap Recovery

### What Was Lost

C, D, E from the bug era cannot be recovered through front sync. Options:

| Option | Action | Effort |
|--------|--------|--------|
| A. Do nothing | Accept the gap | Zero |
| B. Manual | Find bookmark IDs, manually re-add | High |
| C. Backfill from corrupted token | Run backfill from stored token | Medium |

**Recommendation**: Run backfill once after deployment. It will paginate backward from the last stored token and recover any missing bookmarks.

---

## Future Improvements

1. **Increase max_results**: Test with higher values (20-100) if rate limits allow
2. **Backfill completion**: Mark user as "fully synced" after backfill completes
3. **Sync status API**: Return `last_front_sync_time`, `is_backfill_complete` to frontend
4. **Staleness detection**: Warn if sync hasn't run in N hours

---

## Migration

```sql
-- Add new column
ALTER TABLE users ADD COLUMN front_watermark_id VARCHAR(50);

-- Optional: clean up old buggy column
ALTER TABLE users DROP COLUMN front_sync_token;
```

Run alembic:
```bash
alembic revision -m "add_front_watermark_id"
```