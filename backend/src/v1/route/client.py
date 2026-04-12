from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
from src.v1.service.bookmark import BookmarkService
from src.v1.route.dependencies import get_current_user, get_bookmark_service
from src.v1.base.exception import BadRequest
from src.celery.task import front_sync_bookmark_task
from pydantic import BaseModel

logger = get_logger(__name__)
# Router with /client prefix - endpoints for frontend consumption
client_router = APIRouter(prefix="/client")


# Response schema for sync endpoint
class SyncResponse(BaseModel):
    status: str
    message: str


# --------------------------------------------------------------
# GET /client/bookmarks
# --------------------------------------------------------------
# Primary endpoint for frontend to fetch bookmarks.
# Flow:
#   1. Check DB for existing bookmarks
#   2. If DB empty -> fetch from X API, save to DB, then return
#   3. If DB has data -> return from DB with pagination
# --------------------------------------------------------------
@client_router.get("/bookmarks")
async def get_bookmarks(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """
    Get user's bookmarks.
    - If DB has bookmarks: return from DB with pagination
    - If DB is empty: fetch from X API, save to DB, then return
    """
    # Get current user's ID from auth token
    user_id = current_user.id

    # Check how many bookmarks user has in DB
    bookmark_count = await bookmark_service.count_user_bookmarks(db, user_id)
    logger.info(f"User {user_id} has {bookmark_count} bookmarks in DB")

    # --------------------------------------------------------------
    # Case 1: DB is empty -> Fetch from X API (first-time user)
    # --------------------------------------------------------------
    if bookmark_count == 0:
        logger.info(f"DB empty for user {user_id}, fetching from X API")

        # Get valid OAuth tokens for X API calls
        tokens = await get_valid_tokens(user_id, db)
        access_token = tokens.get("access_token")
        x_id = current_user.x_id

        # Validate we have required credentials - raise BadRequest if missing
        if not access_token or not x_id:
            raise BadRequest("Missing credentials for X API")

        # Call X API to get bookmarks
        api_response = await twitter_service.get_bookmarks(
            access_token=access_token,
            user_id=str(user_id),
            x_id=x_id,
            max_results=100,
            pagination_token=None,
        )

        # If X API returns no data, return empty response
        if not api_response.get("data"):
            return {
                "data": [],
                "includes": {"users": []},
                "meta": {"result_count": 0},
            }

        # Save fetched bookmarks to DB (parses & stores in bookmarks, posts, authors tables)
        await bookmark_service.save_bookmarks(
            db,
            str(user_id),
            api_response,
            sync_time=None,
        )

        # Return from DB (applies limit/offset pagination)
        return await bookmark_service.get_bookmarks_from_db(
            db, user_id, limit=limit, offset=offset
        )

    # --------------------------------------------------------------
    # Case 2: DB has data -> Return from DB with pagination
    # --------------------------------------------------------------
    return await bookmark_service.get_bookmarks_from_db(
        db, user_id, limit=limit, offset=offset
    )


# --------------------------------------------------------------
# POST /client/sync
# --------------------------------------------------------------
# Manual sync trigger for user to force refresh bookmarks.
# Enqueues Celery task and returns immediately (async pattern).
# Frontend can poll /client/bookmarks to see updated data.
# --------------------------------------------------------------
@client_router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a manual sync for the user's bookmarks.
    Enqueues the front sync task and returns immediately.
    """
    user_id = str(current_user.id)
    logger.info(f"Manual sync triggered for user_id={user_id}")

    # Enqueue Celery task (background task will fetch from X and update DB)
    front_sync_bookmark_task.delay(user_id)

    # Return immediately - sync happens in background
    return SyncResponse(
        status="queued",
        message="Sync task has been enqueued. Your bookmarks will be updated shortly.",
    )
