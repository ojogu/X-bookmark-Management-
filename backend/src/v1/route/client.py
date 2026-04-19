from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.route.dependencies import get_current_user, get_bookmark_service
from src.v1.schemas import SyncResponse
from src.v1.service.bookmark import BookmarkService

logger = get_logger(__name__)

client_router = APIRouter(prefix="/client", tags=["client"])

from src.v1.route.bookmark import bookmark_router
from src.v1.route.folder import folder_router
from src.v1.route.tag import tag_router
from src.v1.route.user import user_router


@client_router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """
    Trigger a manual sync for the user's bookmarks.
    Enqueues the front sync task and returns immediately.
    """
    from src.celery.task import front_sync_bookmark_task

    user_id = str(current_user.id)
    logger.info(f"Manual sync triggered for user_id={user_id}")

    last_sync = await bookmark_service.get_last_sync_time(db, user_id)

    front_sync_bookmark_task.delay(user_id)

    return SyncResponse(
        status="queued",
        message="Sync task has been enqueued. Your bookmarks will be updated shortly.",
        last_sync_time=last_sync.isoformat() if last_sync else None,
    )


client_router.include_router(bookmark_router)
client_router.include_router(folder_router)
client_router.include_router(tag_router)
client_router.include_router(user_router)
