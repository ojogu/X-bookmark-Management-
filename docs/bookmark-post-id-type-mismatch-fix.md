# Bookmark Post ID Type Mismatch - Root Cause Analysis & Fix

**Date:** April 2026  
**Status:** Resolved  
**Author:** Engineering Team

---

## Problem Statement

The front sync worker was failing with a PostgreSQL type error:

```
sqlalchemy.exc.DBAPIError: invalid input for query argument $2: '2044804880137584783'
(invalid UUID '2044804880137584783': length must be between 32..36 characters, got 19)

SQL: SELECT bookmarks.post_id FROM bookmarks
WHERE bookmarks.user_id = $1::UUID AND bookmarks.post_id IN ($2::UUID, $3::UUID)
```

The X/Twitter post IDs (19-digit strings like `2044804880137584783`) were being cast as UUIDs, causing the query to fail.

---

## Root Cause Analysis

### Data Model Mismatch

The system has two different ID types for posts:

| Column | Type | Example Value |
|--------|------|---------------|
| `Post.id` | UUID | `0922fbb2-339b-4df1-b4cf-7cc95520029d` (internal DB primary key) |
| `Post.post_id` | String | `2044804880137584783` (X/Twitter API ID) |
| `Bookmark.post_id` | UUID | Foreign key to `Post.id` (internal UUID) |

### The Bug

In `src/celery/task.py`, the front sync checks which bookmarks already exist:

```python
# X/Twitter returns string IDs like '2044804880137584783'
post_ids = [b["id"] for b in bookmarks]

# Query incorrectly uses these strings against a UUID column
existing_ids = await bookmark_service.get_existing_post_ids(session, user_id, post_ids)
```

The `get_existing_post_ids` method was querying `BookmarkModel.post_id` (a UUID column) directly against the X/Twitter string IDs:

```python
# Before: Broken query
result = await db.execute(
    sa.select(BookmarkModel.post_id).where(
        BookmarkModel.user_id == user_id,
        BookmarkModel.post_id.in_(post_ids),  # UUID column ← String IDs (fail)
    )
)
```

When saving bookmarks (working correctly):

```python
# Step 1: Look up post by X/Twitter ID (Post.post_id string column)
post = await self.check_if_post_exists(db, post_data["id"])

# Step 2: Store internal UUID (Post.id) in Bookmark
bookmark = BookmarkModel(user_id=user_id, post_id=post.id)  # UUID ← correct
```

So bookmarks correctly store internal UUIDs, but the existence check was comparing against X/Twitter string IDs.

---

## Solution Implemented

Replace the direct `BookmarkModel.post_id` query with a JOIN that resolves the internal UUIDs:

```python
async def get_existing_post_ids(self, db: AsyncSession, user_id: UUID, post_ids: list) -> set:
    if not post_ids:
        return set()

    result = await db.execute(
        sa.select(PostModel.post_id)
        .join(BookmarkModel, BookmarkModel.post_id == PostModel.id)
        .where(
            BookmarkModel.user_id == user_id,
            PostModel.post_id.in_(post_ids),
        )
    )
    return set(row[0] for row in result.fetchall())
```

**How it works:**
1. Join `PostModel` with `BookmarkModel` on `BookmarkModel.post_id == PostModel.id`
2. Filter by `PostModel.post_id` (X/Twitter string IDs)
3. Return X/Twitter string IDs to match what `task.py` passes in

---

## Tradeoffs & Considerations

### Solution Tradeoffs

| Pros | Cons |
|------|------|
| Single query (JOIN) | Slightly more complex than direct query |
| No call site changes needed | - |
| Returns correct type (strings) | - |
| Reuses existing index on `Post.post_id` | - |

### Alternative Approaches Considered

**Option B: Two-step lookup**
1. Query `Post.id` by `Post.post_id` strings
2. Query `BookmarkModel.post_id` by those UUIDs

This would require two queries and returning a different type than the caller expects.

**Option C: Add X/Twitter ID to Bookmark table**
Add a `post_id_from_x` column to store X/Twitter IDs directly — but this adds redundancy and storage overhead.

The JOIN approach (Option A) was chosen as it:
- Minimizes code changes
- Uses existing relationships
- Returns the expected type (strings)

---

## Monitoring Recommendations

1. **Query performance:** The JOIN adds a JOIN clause but should leverage existing indexes on both `posts.post_id` and `bookmarks.post_id`
2. **Watch for similar issues:** Search for other places where X/Twitter IDs might be compared against UUID columns

---

## Files Changed

| File | Change |
|------|--------|
| `src/v1/service/bookmark.py` | Fixed `get_existing_post_ids` to use JOIN |

---

## Conclusion

The bug was a **type mismatch** between X/Twitter string IDs and the internal UUID column in the Bookmark model. The fix uses a JOIN to correctly resolve the internal UUIDs from X/Twitter string IDs, keeping the call site unchanged.