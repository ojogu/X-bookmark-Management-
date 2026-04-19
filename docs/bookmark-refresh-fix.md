# Bookmark Refresh Fix - Engineering Doc

## Problem Statement

### The Bug: Stale Data Not Refreshing

Users were experiencing an issue where the bookmarks page showed outdated data even after:
- Refreshing the browser
- New bookmarks being added to the database via background sync
- Waiting for the background sync to complete

**Root Cause Analysis:**

1. **React Query Caching (Frontend)**
   - `staleTime` was set to 60 seconds (1 minute)
   - Data was considered "fresh" for 60 seconds after fetching
   - During this period, ANY page refresh would serve cached data without calling the API

2. **No Window Focus Refetch**
   - When users switched tabs and returned to the app, no refetch occurred
   - Users expected data to update when they came back to the page

3. **No Manual Refresh Option**
   - Users had no way to trigger a manual refresh
   - They had to wait for the 60-second cache to expire
   - Background sync ran but users couldn't see the results until cache expired

4. **No Sync Status Visibility**
   - Users didn't know if sync was running
   - No indication of when data was last updated
   - No feedback during manual sync operations

### User Impact

| Scenario | Before | User Experience |
|----------|--------|------------------|
| Open bookmarks page | Fetch from API, cache for 60s | OK |
| Refresh after 30s | Returns cached data | "Wait, shouldn't it be updated?" |
| Switch tabs, come back | Uses stale cached data | "Why isn't it updating?" |
| Click manual sync | No button exists | Can't force refresh |
| Background sync runs | UI unchanged | "Did it work?" |

---

## Solution: Caching Fix + Manual Refresh

### Overview

We implemented a multi-layered solution:

1. **Reduced staleTime** - Data goes stale faster → more frequent auto-refresh
2. **Added refetchOnWindowFocus** - Refetch when returning to the tab
3. **Manual sync button** - Users can trigger sync anytime
4. **Sync status polling** - Detect when sync completes, then refetch
5. **Last synced timestamp** - Show users when data was last updated

### Solution Components

#### 1. Reduced Cache Stale Time

**Before:**
```typescript
// main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,  // 60 seconds
    },
  },
})
```

**After:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10 * 1000,  // 10 seconds
      refetchOnWindowFocus: true,  // Refetch when user returns to tab
      retry: 1,
    },
  },
})
```

**Trade-off:**
- **Pros:** Data refreshes more frequently, users see updates faster
- **Cons:** More API calls, slightly higher server load
- **Rationale:** The trade-off is acceptable because bookmarks are user-generated content that benefits from fresher data, and the API calls are lightweight (DB queries)

#### 2. Manual Sync Button

Users can click a sync button to manually trigger a background sync.

**Behavior:**
1. Click sync → button shows "Syncing..." with spinning icon
2. Backend triggers Celery task (fire-and-forget)
3. Frontend polls `/sync-status` every 1 second
4. When `last_sync_time` changes → cache invalidates → refetch
5. User sees updated bookmarks

**UI Location:** Next to the search/sort/filter controls in the toolbar

#### 3. Sync Status Polling

The frontend detects when sync completes by comparing timestamps:

```typescript
// Capture timestamp before triggering sync
const lastSyncBefore = response.last_sync_time

// Poll until timestamp changes
const poll = setInterval(async () => {
  const status = await fetchSyncStatus()
  
  if (status.last_sync_time !== lastSyncBefore) {
    clearInterval(poll)
    invalidateCache()  // Sync done, refetch
  }
}, 1000)
```

**Why this approach?**
- No backend changes needed to detect sync completion
- Uses existing `/sync-status` endpoint
- Polling is lightweight (single DB query per poll)

#### 4. Last Synced Timestamp

Display when data was last updated:

```
Last synced: 5m ago
```

**Format:**
- < 1 min: "Just now"
- < 60 min: "Xm ago"
- < 24 hours: "Xh ago"
- > 24 hours: "Xd ago"
- Never synced: "Never"

---

## Trade-offs

| Decision | Trade-off | Rationale |
|----------|-----------|-----------|
| staleTime: 60s → 10s | More DB queries, but fresher data | Acceptable - bookmarks don't change that often, but users expect fresher data |
| Polling /sync-status every 1s | Extra API calls during sync | Only during manual sync, max ~30s, lightweight |
| Show "Syncing..." state | Complexity in UI | Critical for user feedback - they need to know sync is happening |
| Invalidate cache on sync complete | Extra refetch | Ensures users see new data immediately |

### Alternative Approaches Considered

| Approach | Why Not Chosen |
|----------|---------------|
| Use Celery task ID to track status | Requires Celery result backend, more complex |
| Long-polling instead of short-polling | More server resources, not needed for this use case |
| WebSocket for real-time updates | Overkill for this feature, adds infrastructure complexity |
| Only manual refresh without auto-refresh | Users expect data to update when they return to the tab |

---

## Implementation Details

### Backend Changes

**File: `src/v1/schemas/client.py`**
```python
from typing import Optional

class SyncResponse(BaseModel):
    status: str
    message: str
    last_sync_time: Optional[str] = None  # NEW: timestamp before sync
```

**File: `src/v1/route/client.py`**
```python
@client_router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    # Get current sync time BEFORE triggering
    bookmark_service = BookmarkService(db=db)
    last_sync = await bookmark_service.get_last_sync_time(db, user_id)

    front_sync_bookmark_task.delay(user_id)

    return SyncResponse(
        status="queued",
        message="Sync task has been enqueued. Your bookmarks will be updated shortly.",
        last_sync_time=last_sync.isoformat() if last_sync else None
    )
```

### Frontend Changes

**File: `src/main.tsx`**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10 * 1000,
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})
```

**File: `src/types/index.ts`**
```typescript
export interface SyncStatus {
  last_sync_time: string | null
  is_backfill_complete: boolean
}

export interface SyncResponse {
  status: string
  message: string
  last_sync_time?: string | null
}
```

**File: `src/features/bookmarks/hooks.ts`**

New hooks:
- `useSyncStatus()` - Fetch sync status with polling
- `useManualSync()` - Trigger manual sync with completion detection

**File: `src/components/bookmarks/BookmarkToolbar.tsx`**

Added:
- Refresh/Sync button with loading state
- "Last synced: X ago" display
- Integration with `useManualSync` hook

---

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/client/sync` | POST | Trigger background sync |
| `/client/bookmarks/sync-status` | GET | Get sync status (last_sync_time, is_backfill_complete) |
| `/client/bookmarks` | GET | Fetch bookmarks (existing) |

---

## User Experience Flow

### Scenario 1: Auto-refresh on page load
```
1. User opens bookmarks page
2. React Query checks: is data stale? (> 10 seconds)
3. If stale → fetch fresh data from API
4. Display bookmarks
```

### Scenario 2: Auto-refresh on tab focus
```
1. User is on bookmarks page
2. User switches to another tab
3. User returns to bookmarks tab
4. refetchOnWindowFocus triggers → fetch fresh data
5. Display updated bookmarks
```

### Scenario 3: Manual sync
```
1. User clicks "Sync" button
2. Button shows "Syncing..." state
3. Frontend calls POST /client/sync
4. Backend returns last_sync_time before sync
5. Frontend starts polling GET /sync-status
6. Sync completes → last_sync_time changes
7. Frontend detects change → invalidates cache
8. React Query refetches bookmarks
9. Button returns to idle, user sees new data
```

---

## Future Improvements

1. **Optimistic sync status**: Show progress percentage during initial backfill
2. **Push notifications**: Notify when sync completes (for long-running syncs)
3. **Background sync interval**: Auto-sync more frequently for active users
4. **Sync status in sidebar**: Show indicator in nav when sync is running
5. **Conflict resolution**: Handle cases where bookmark is deleted on X but still in DB