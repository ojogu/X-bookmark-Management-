import asyncio
from contextlib import asynccontextmanager
from src.utils.log import setup_logger
from .celery import bg_task
from src.v1.service.twitter import TwitterService 
from src.v1.service.user import UserService 
from src.v1.service.utils import get_valid_tokens
from src.utils.db import get_db_session_no_context


@asynccontextmanager
async def get_db_session():
    db = await get_db_session_no_context()
    try:
        yield db
    finally:
        await db.close()

user_service_global = UserService(db=None) # Placeholder, will be initialized in task
twitter_service = TwitterService()


logger = setup_logger(__name__, file_path="bg_tasks.log")

#cron job(celery beat) to fetch user id
@bg_task.task(bind=True)
def fetch_user_id_task(self):
    logger.info("Starting fetch_user_id_task")
    try:
        async def _internal():
            async with get_db_session() as db:
                user_service = UserService(db=db)
                user_ids = await user_service.fetch_all_users_id()
                logger.info(f"Fetched {len(user_ids)} user IDs.")
                for user_id in user_ids:
                    logger.info(f"Enqueuing fetch_write_bookmark_task for user_id: {user_id}")
                    fetch_write_bookmark_task.delay(user_id)  # call .delay on the task
        return asyncio.run(_internal())
    except Exception as e:
        logger.error(f"Error in fetch_user_id_task: {e}", exc_info=True)
        raise # Re-raise the exception to mark the task as failed
    finally:
        logger.info("Finished fetch_user_id_task")
    
  
#define celery task to read bookmarks from the api and write to the db

@bg_task.task(bind=True)
def fetch_write_bookmark_task(self, user_id):
    logger.info(f"Starting fetch_write_bookmark_task for user_id: {user_id}")
    try:
        async def _internal():
            async with get_db_session() as db:
                user_service = UserService(db=db) # Re-initialize user_service with the current db session
                # Assuming get_valid_tokens needs the db session
                tokens = await get_valid_tokens(user_id, db) 
                if not tokens:
                    logger.warning(f"No valid tokens found for user_id: {user_id}. Skipping bookmark fetch.")
                    return

                access_token = tokens.get("access_token")
                x_id = tokens.get("x_id")

                if not access_token or not x_id:
                    logger.warning(f"Missing access_token or x_id for user_id: {user_id}. Access Token present: {bool(access_token)}, X-ID present: {bool(x_id)}. Skipping bookmark fetch.")
                    return
                
                bookmarks = await twitter_service.get_bookmarks(
                    access_token=access_token,
                    x_id=x_id,
                    user_id=user_id,
                    max_results=5,
                )
                logger.info(f"Successfully fetched {len(bookmarks)} bookmarks for user_id: {user_id}")
                logger.debug(f"Fetched bookmarks for user_id {user_id}: {bookmarks}")
                # TODO: write bookmarks to DB
                logger.info(f"Bookmarks for user_id {user_id} are ready to be written to DB.")

        return asyncio.run(_internal())
    except Exception as e:
        logger.error(f"Error in fetch_write_bookmark_task for user_id {user_id}: {e}", exc_info=True)
        raise # Re-raise the exception to mark the task as failed
    finally:
        logger.info(f"Finished fetch_write_bookmark_task for user_id: {user_id}")
