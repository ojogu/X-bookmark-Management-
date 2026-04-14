from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.user import UserService
from src.v1.route.dependencies import get_current_user
from pydantic import BaseModel

logger = get_logger(__name__)

client_router = APIRouter(prefix="/client", tags=["client"])

from src.v1.route.bookmark import bookmark_router
from src.v1.route.folder import folder_router
from src.v1.route.tag import tag_router


class SyncResponse(BaseModel):
    status: str
    message: str


@client_router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a manual sync for the user's bookmarks.
    Enqueues the front sync task and returns immediately.
    """
    from src.celery.task import front_sync_bookmark_task

    user_id = str(current_user.id)
    logger.info(f"Manual sync triggered for user_id={user_id}")

    front_sync_bookmark_task.delay(user_id)

    return SyncResponse(
        status="queued",
        message="Sync task has been enqueued. Your bookmarks will be updated shortly.",
    )


@client_router.get("/user/info")
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get current user profile info."""
    user_service = UserService(db=db)
    user_info = await user_service.get_user_info(str(current_user.id))
    return user_info


client_router.include_router(bookmark_router)
client_router.include_router(folder_router)
client_router.include_router(tag_router)
