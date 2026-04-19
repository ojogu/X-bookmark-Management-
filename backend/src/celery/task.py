import asyncio
from contextlib import asynccontextmanager

from celery import shared_task
import concurrent
from src.utils.log import get_logger
from .celery import bg_task
from src.v1.service.twitter import TwitterService
from src.v1.service.user import UserService
from src.v1.service.utils import get_valid_tokens
from src.utils.db import get_async_db_session
from src.v1.service.bookmark import BookmarkService
from src.utils.redis import get_redis_sync
from datetime import datetime
import logging

# --------------------------
# Rate Limiting Configuration
# --------------------------
# Maximum concurrent sync tasks allowed per user within the time window.
# Prevents a single user from overwhelming the X API or Celery workers.
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60  # seconds - sliding window before counter resets
RATE_LIMIT_RETRY_DELAY = 180  # seconds - wait before retry when rate limited


def is_rate_limited(
    user_id: str, limit: int = RATE_LIMIT, window: int = RATE_LIMIT_WINDOW
) -> bool:
    """
    Check if a user has exceeded the rate limit for sync tasks.

    Uses Redis INCR for atomic counter increment - simple and race-condition free.
    Each user has their own counter key, so rate limits are per-user isolated.

    Args:
        user_id: The user ID to check rate limit for
        limit: Maximum requests allowed per window (default: 5)
        window: Time window in seconds (default: 60)

    Returns:
        True if user is rate limited (exceeded limit), False if allowed
    """
    r = get_redis_sync()
    # Unique key per user ensures isolation - one user's limit doesn't affect others
    key = f"rate_limit:sync:{user_id}"
    current = r.incr(key)
    # Set TTL on first request to auto-reset the counter after window expires
    if current == 1:
        r.expire(key, window)
    return current > limit


# @asynccontextmanager
# async def get_db_db():
#     db = await get_db_db_no_context()
#     try:
#         yield db
#     finally:
#         await db.close()

user_service_global = UserService(db=None)  # Placeholder, will be initialized in task
twitter_service = TwitterService()


# Configure logging for Celery workers using structlog
logger = get_logger(__name__)


def run_async_in_sync(coro):
    """
    Helper function to run async code in sync Celery tasks
    Creates a new event loop in a separate thread to avoid conflicts
    """

    def _run_in_thread():
        # Create a fresh event loop in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # Run in a separate thread to avoid event loop conflicts
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_in_thread)
        return future.result()

    # --------------------------
    # Front sync Task
    # --------------------------
    """
    Frontsync (or forward sync) fetches new/recent data from the source — data that has arrived since the last sync. It keeps the system current by pulling the leading edge of new records.

    Flow: Fetch newest -> bulk-check against DB -> stop at boundary -> save new.
    """


@shared_task(bind=True)
def fetch_user_id_for_front_sync_task(self):
    """
    Celery beat cron job.
    - Fetches all user IDs from DB
    - Enqueues front_sync_bookmark_task for each user
    """

    async def _fetch_user_ids():
        try:
            async with get_async_db_session() as db:
                user_service = UserService(db)
                user_ids = await user_service.fetch_all_users_id()

            logger.info(f"Fetched {len(user_ids)} user IDs.")

            for user_id in user_ids:
                logger.info(f"Enqueuing front_sync_bookmark_task for user_id={user_id}")
                front_sync_bookmark_task.delay(user_id)

            return {"fetched": len(user_ids)}

        except Exception as e:
            logger.error(f"Error in fetch_user_id_task: {e}", exc_info=True)
            raise

    return run_async_in_sync(_fetch_user_ids())


@shared_task(bind=True, max_retries=3)
def front_sync_bookmark_task(self, user_id):
    """
    Front sync fetches NEW bookmarks from X API.

    STATE:
    - front_watermark_id: ID of newest bookmark seen (NULL on cold start)
    - backfill_cursor: pagination token for backfill worker

    ON EACH RUN:
    1. Fetch page 1 from X API (no pagination token, max_results=2)
    2. IF front_watermark_id IS NULL (cold start):
         - Save all bookmarks from page 1
         - Set front_watermark_id = first bookmark's post_id (newest)
         - Set backfill_cursor = next_token from this response
         - STOP (do not paginate further)
    3. IF front_watermark_id IS SET (subsequent runs):
         - Bulk-check all post_ids on page against DB
         - Walk through bookmarks: hit existing → STOP, else collect new
         - IF entire page is new AND next_token exists: fetch next page (edge case)
         - Save collected new bookmarks
         - Update front_watermark_id = newest post_id from collected
    """
    if is_rate_limited(str(user_id)):
        logger.warning(
            f"Rate limited for user_id={user_id}, retrying in {RATE_LIMIT_RETRY_DELAY}s"
        )
        raise self.retry(countdown=RATE_LIMIT_RETRY_DELAY)

    async def _front_sync_bookmarks():
        try:
            async with get_async_db_session() as db:
                user_service = UserService(db)
                bookmark_service = BookmarkService(db=db, user_service=user_service)

                tokens = await get_valid_tokens(user_id, db)
                if not tokens:
                    logger.warning(f"No valid tokens for user_id={user_id}. Skipping.")
                    return {"user_id": user_id, "status": "no_tokens"}

                access_token = tokens.get("access_token")
                x_id = tokens.get("x_id")
                if not access_token or not x_id:
                    logger.warning(
                        f"Missing access_token/x_id for user_id={user_id}. Skipping."
                    )
                    return {"user_id": user_id, "status": "missing_credentials"}

                current_time = datetime.now()

                # Check if cold start (first run ever)
                front_watermark_id = await bookmark_service.fetch_front_watermark_id(
                    db, user_id
                )
                is_cold_start = front_watermark_id is None

                # Fetch first page (newest bookmarks)
                response = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    user_id=user_id,
                    x_id=x_id,
                    max_results=2,
                )

                bookmarks = response.get("data", [])
                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                logger.info(
                    f"Front sync: cold_start={is_cold_start}, fetched={len(bookmarks)} bookmarks"
                )

                if not bookmarks:
                    logger.info(f"No bookmarks found for user_id={user_id}")
                    return {
                        "user_id": user_id,
                        "bookmarks": 0,
                        "status": "no_bookmarks",
                    }

                # COLD START: Save all, store watermark + backfill cursor
                if is_cold_start:
                    await bookmark_service.save_bookmarks(
                        db,
                        user_id,
                        response,
                        sync_time=current_time,
                    )

                    # Store watermark (newest bookmark ID)
                    newest_id = bookmarks[0]["id"]
                    await bookmark_service.update_front_watermark_id(
                        db, user_id, newest_id
                    )

                    # Store backfill cursor (for backfill worker to continue)
                    if next_token:
                        await bookmark_service.update_backfill_cursor(
                            db, user_id, next_token
                        )
                        logger.info(
                            f"Front sync: stored backfill_cursor for user_id={user_id}"
                        )

                    return {
                        "user_id": user_id,
                        "bookmarks": len(bookmarks),
                        "status": "cold_start_done",
                    }

                # SUBSEQUENT RUNS: Check against watermark
                post_ids = [b["id"] for b in bookmarks]
                existing_ids = await bookmark_service.get_existing_post_ids(
                    db, user_id, post_ids
                )

                # Walk through: hit existing = boundary
                new_bookmarks = []
                for bookmark in bookmarks:
                    if bookmark["id"] in existing_ids:
                        break  # boundary reached
                    new_bookmarks.append(bookmark)

                # Edge case: entire page is new, fetch next page
                if not new_bookmarks and next_token:
                    logger.info(f"Front sync: fetching next page for user_id={user_id}")
                    response2 = await twitter_service.get_bookmarks(
                        access_token=access_token,
                        user_id=user_id,
                        x_id=x_id,
                        max_results=2,
                        pagination_token=next_token,
                    )
                    bookmarks2 = response2.get("data", [])
                    meta2 = response2.get("meta", {})

                    post_ids2 = [b["id"] for b in bookmarks2]
                    existing_ids2 = await bookmark_service.get_existing_post_ids(
                        db, user_id, post_ids2
                    )
                    for bm in bookmarks2:
                        if bm["id"] in existing_ids2:
                            break
                        new_bookmarks.append(bm)

                    if new_bookmarks:
                        response = {"data": new_bookmarks, "meta": meta2}

                # Save collected new bookmarks
                if new_bookmarks:
                    await bookmark_service.save_bookmarks(
                        db,
                        user_id,
                        {"data": new_bookmarks, "meta": meta},
                        sync_time=current_time,
                    )

                    # Update watermark to newest from collected
                    newest_id = new_bookmarks[0]["id"]
                    await bookmark_service.update_front_watermark_id(
                        db, user_id, newest_id
                    )
                    logger.info(
                        f"Front sync: saved {len(new_bookmarks)} new, watermark={newest_id}"
                    )

                await bookmark_service.update_last_sync_time(db, user_id, current_time)

                return {
                    "user_id": user_id,
                    "bookmarks": len(new_bookmarks),
                    "status": "success",
                }

        except Exception as e:
            logger.error(
                f"Error in front_sync_bookmark_task for user_id={user_id}: {e}",
                exc_info=True,
            )
            raise

    return run_async_in_sync(_front_sync_bookmarks())

    # --------------------------
    # BackFill Task
    # --------------------------


@shared_task(bind=True)
def fetch_user_id_for_backfill_task(self):
    """
    Celery beat job for scheduling backfill tasks.
    Runs less frequently than front sync (e.g., every 15 mins / hourly).
    Backfill fetches historical data — records that predate the initial sync or that were missed. It fills in the past, working backward (or forward through older time ranges) to achieve completeness.

    """

    async def _fetch_user_ids():
        async with get_async_db_session() as db:
            user_service = UserService(db)
            user_ids = await user_service.fetch_pending_backfill_user_ids()

        for user_id in user_ids:
            backfill_bookmark_task.delay(user_id)

        return {"queued": len(user_ids)}

    return run_async_in_sync(_fetch_user_ids())


@shared_task(bind=True, max_retries=3)
def backfill_bookmark_task(self, user_id):
    """
    Celery task to fetch historical bookmarks using pagination token.
    Uses next_token stored in DB for pagination.
    Re-queues itself when there's a next_token for continuous fetching.
    Sets is_backfill_complete when all pages are exhausted.

    Rate Limiting:
        - Per-user concurrency limited to RATE_LIMIT (5) requests per RATE_LIMIT_WINDOW (60s)
        - If rate limited, task retries after RATE_LIMIT_RETRY_DELAY (180s)
    """
    # Check rate limit before starting - prevents concurrent task flooding
    if is_rate_limited(str(user_id)):
        logger.warning(
            f"Rate limited for user_id={user_id}, retrying in {RATE_LIMIT_RETRY_DELAY}s"
        )
        raise self.retry(countdown=RATE_LIMIT_RETRY_DELAY)

    async def _fetch_back_fill_bookmarks():
        try:
            async with get_async_db_session() as db:
                user_service = UserService(db)
                bookmark_service = BookmarkService(db=db, user_service=user_service)

                tokens = await get_valid_tokens(user_id, db)
                if not tokens:
                    logger.warning(f"No valid tokens for user_id={user_id}. Skipping.")
                    return {"user_id": user_id, "status": "no_tokens"}

                access_token = tokens.get("access_token")
                x_id = tokens.get("x_id")
                if not access_token or not x_id:
                    logger.warning(
                        f"Missing access_token/x_id for user_id={user_id}. Skipping."
                    )
                    return {"user_id": user_id, "status": "missing_credentials"}

                next_token = await bookmark_service.fetch_next_token(db, user_id)
                logger.info(f"Backfill for user_id={user_id}, next_token={next_token}")

                response = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    user_id=user_id,
                    x_id=x_id,
                    max_results=2,
                    pagination_token=next_token,
                )

                bookmarks = response.get("data", [])
                meta = response.get("meta", {})
                response_next_token = meta.get("next_token")

                logger.info(
                    f"Backfill fetched {len(bookmarks)} bookmarks, next_token={response_next_token}"
                )

                if not bookmarks:
                    await bookmark_service.mark_backfill_complete(db, user_id)
                    logger.info(f"Backfill complete for user_id={user_id}")
                    return {
                        "user_id": user_id,
                        "bookmarks": 0,
                        "status": "complete",
                        "has_more": False,
                    }

                await bookmark_service.save_bookmarks(
                    db, user_id, response, next_token=response_next_token
                )

                if response_next_token:
                    logger.info(
                        f"More pages available, re-queuing backfill_bookmark_task for user_id={user_id}"
                    )
                    backfill_bookmark_task.delay(user_id)

                return {
                    "user_id": user_id,
                    "bookmarks": len(bookmarks),
                    "status": "success",
                    "has_more": bool(response_next_token),
                }

        except Exception as e:
            logger.error(
                f"Error in backfill_bookmark_task for user_id={user_id}: {e}",
                exc_info=True,
            )
            raise

    return run_async_in_sync(_fetch_back_fill_bookmarks())
