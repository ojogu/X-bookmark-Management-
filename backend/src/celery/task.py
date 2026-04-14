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
from datetime import datetime
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)

# @asynccontextmanager
# async def get_db_session():
#     db = await get_db_session_no_context()
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
    
    Pagination: Uses front_sync_token stored in DB to paginate through results.
    Re-queues itself when more pages are available.
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
            async with get_async_db_session() as session:
                user_service = UserService(session)
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


@shared_task(bind=True)
@retry(
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
def front_sync_bookmark_task(self, user_id):
    """
    Celery task to fetch new bookmarks from X API using pagination.
    Uses front_sync_token stored in DB for pagination.
    Re-queues itself when there's a next_token for continuous fetching.
    """

    async def _front_sync_bookmarks():
        try:
            async with get_async_db_session() as session:
                user_service = UserService(session)
                bookmark_service = BookmarkService(user_service)

                tokens = await get_valid_tokens(user_id, session)
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

                front_sync_token = await bookmark_service.fetch_front_sync_token(
                    session, user_id
                )
                current_time = datetime.now()

                logger.info(
                    f"Front sync for user_id={user_id}, front_sync_token={front_sync_token}"
                )

                response = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    user_id=user_id,
                    x_id=x_id,
                    max_results=10,
                    pagination_token=front_sync_token,
                )

                bookmarks = response.get("data", [])
                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                logger.info(
                    f"Front sync fetched {len(bookmarks)} bookmarks, next_token={next_token}"
                )

                if not bookmarks and next_token is None:
                    logger.info(f"No bookmarks found for user_id={user_id}")
                    return {
                        "user_id": user_id,
                        "bookmarks": 0,
                        "status": "no_bookmarks",
                        "has_more": False,
                    }

                if bookmarks:
                    await bookmark_service.save_bookmarks(
                        session,
                        user_id,
                        response,
                        sync_time=current_time,
                        next_token=next_token,
                    )

                if next_token:
                    logger.info(
                        f"More pages available, re-queuing front_sync_bookmark_task for user_id={user_id}"
                    )
                    front_sync_bookmark_task.delay(user_id)

                return {
                    "user_id": user_id,
                    "bookmarks": len(bookmarks),
                    "status": "success",
                    "has_more": bool(next_token),
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
        async with get_async_db_session() as session:
            user_service = UserService(session)
            user_ids = await user_service.fetch_pending_backfill_user_ids()

        for user_id in user_ids:
            backfill_bookmark_task.delay(user_id)

        return {"queued": len(user_ids)}

    return run_async_in_sync(_fetch_user_ids())


@shared_task(bind=True)
@retry(
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
    reraise=True,
)
def backfill_bookmark_task(self, user_id):
    """
    Celery task to fetch historical bookmarks using pagination token.
    Uses next_token stored in DB for pagination.
    Re-queues itself when there's a next_token for continuous fetching.
    Sets is_backfill_complete when all pages are exhausted.
    """

    async def _fetch_back_fill_bookmarks():
        try:
            async with get_async_db_session() as session:
                user_service = UserService(session)
                bookmark_service = BookmarkService(user_service)

                tokens = await get_valid_tokens(user_id, session)
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

                next_token = await bookmark_service.fetch_next_token(session, user_id)
                logger.info(f"Backfill for user_id={user_id}, next_token={next_token}")

                response = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    user_id=user_id,
                    x_id=x_id,
                    max_results=10,
                    pagination_token=next_token,
                )

                bookmarks = response.get("data", [])
                meta = response.get("meta", {})
                response_next_token = meta.get("next_token")

                logger.info(
                    f"Backfill fetched {len(bookmarks)} bookmarks, next_token={response_next_token}"
                )

                if not bookmarks:
                    await bookmark_service.mark_backfill_complete(session, user_id)
                    logger.info(f"Backfill complete for user_id={user_id}")
                    return {
                        "user_id": user_id,
                        "bookmarks": 0,
                        "status": "complete",
                        "has_more": False,
                    }

                await bookmark_service.save_bookmarks(
                    session, user_id, response, next_token=response_next_token
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
