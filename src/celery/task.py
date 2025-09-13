import asyncio
from contextlib import asynccontextmanager

from celery import shared_task
import concurrent
from src.utils.log import setup_logger
from .celery import bg_task
from src.v1.service.twitter import TwitterService 
from src.v1.service.user import UserService 
from src.v1.service.utils import get_valid_tokens
from src.utils.db import get_async_db_session
from asgiref.sync import async_to_sync

# @asynccontextmanager
# async def get_db_session():
#     db = await get_db_session_no_context()
#     try:
#         yield db
#     finally:
#         await db.close()

user_service_global = UserService(db=None) # Placeholder, will be initialized in task
twitter_service = TwitterService()


logger = setup_logger(__name__, file_path="bg_tasks.log")


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

@shared_task(bind=True)
def fetch_user_id_task(self):
    """
    Celery beat cron job.
    - Fetches all user IDs from DB
    - Enqueues fetch_write_bookmark_task for each user
    """
    async def _fetch_user_ids():
        try:
            async with get_async_db_session() as session:
                user_service = UserService(session)
                user_ids = await user_service.fetch_all_users_id()

            logger.info(f"Fetched {len(user_ids)} user IDs.")

            for user_id in user_ids:
                logger.info(f"Enqueuing fetch_write_bookmark_task for user_id={user_id}")
                fetch_write_bookmark_task.delay(user_id)

            return {"fetched": len(user_ids)}

        except Exception as e:
            logger.error(f"Error in fetch_user_id_task: {e}", exc_info=True)
            raise

    return run_async_in_sync(_fetch_user_ids())


@shared_task(bind=True)
def fetch_write_bookmark_task(self, user_id):
    """
    Celery task to read bookmarks from the API and write to the DB
    """
    async def _fetch_write_bookmarks():
        try:
            # Use your mentor's session factory
            async with get_async_db_session() as session:
                tokens = await get_valid_tokens(user_id, session)
                if not tokens:
                    logger.warning(f"No valid tokens for user_id={user_id}. Skipping.")
                    return {"user_id": user_id, "status": "no_tokens"}

                access_token = tokens.get("access_token")
                x_id = tokens.get("x_id")
                if not access_token or not x_id:
                    logger.warning(f"Missing access_token/x_id for user_id={user_id}. Skipping.")
                    return {"user_id": user_id, "status": "missing_credentials"}

                #TODO: check for latest next token in the db, if any pass it to fetch the next post, to fetch latest post
                bookmarks = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    x_id=x_id,
                    user_id=user_id,
                    max_results=2,
                )
                logger.info(f"Fetched {len(bookmarks)} bookmarks for user_id={user_id}")

                # TODO: write to DB here
                return {"user_id": user_id, "bookmarks": len(bookmarks), "status": "success"}

        except Exception as e:
            logger.error(f"Error in fetch_write_bookmark_task for user_id={user_id}: {e}", exc_info=True)
            raise

    return run_async_in_sync(_fetch_write_bookmarks())