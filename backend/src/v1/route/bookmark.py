from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
from src.v1.service.bookmark import BookmarkService
from src.v1.route.dependencies import get_current_user, get_bookmark_service
from src.v1.base.exception import BadRequest
from pydantic import BaseModel
from typing import Optional

logger = get_logger(__name__)

bookmark_router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


class MarkReadRequest(BaseModel):
    is_read: bool


class BookmarkFolderRequest(BaseModel):
    folder_id: str


class BookmarkTagRequest(BaseModel):
    tag_id: str


@bookmark_router.get("")
async def get_bookmarks(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = Query(None, description="Full-text search"),
    sort: Optional[str] = Query(
        "date-desc", description="Sort: date-desc, date-asc, alpha-asc, alpha-desc"
    ),
    tags: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    folder_id: Optional[str] = Query(None, description="Filter by folder ID"),
    unread: Optional[bool] = Query(None, description="Filter only unread bookmarks"),
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """
    Get user's bookmarks.
    - If DB has bookmarks: return from DB with pagination
    - If DB is empty: fetch from X API, save to DB, then return
    """
    user_id = current_user.id

    tag_ids = tags.split(",") if tags else []

    bookmark_count = await bookmark_service.count_user_bookmarks(db, user_id)
    logger.info(f"User {user_id} has {bookmark_count} bookmarks in DB")

    if bookmark_count == 0:
        logger.info(f"DB empty for user {user_id}, fetching from X API")

        tokens = await get_valid_tokens(user_id, db)
        access_token = tokens.get("access_token")
        x_id = current_user.x_id

        if not access_token or not x_id:
            raise BadRequest("Missing credentials for X API")

        api_response = await twitter_service.get_bookmarks(
            access_token=access_token,
            user_id=str(user_id),
            x_id=x_id,
            max_results=100,
            pagination_token=None,
        )

        if not api_response.get("data"):
            return {
                "data": [],
                "includes": {"users": []},
                "meta": {"result_count": 0},
            }

        await bookmark_service.save_bookmarks(
            db,
            str(user_id),
            api_response,
            sync_time=None,
        )

        return await bookmark_service.get_bookmarks_from_db(
            db,
            user_id,
            limit=limit,
            offset=offset,
            search=search,
            sort=sort,
            tag_ids=tag_ids,
            folder_id=folder_id,
            unread=unread,
        )

    return await bookmark_service.get_bookmarks_from_db(
        db,
        user_id,
        limit=limit,
        offset=offset,
        search=search,
        sort=sort,
        tag_ids=tag_ids,
        folder_id=folder_id,
        unread=unread,
    )


@bookmark_router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a bookmark from both SaveStack DB and X API.
    X API is source of truth - if X API fails, abort and keep local record.
    """
    user_id = current_user.id
    x_id = current_user.x_id
    logger.info(f"Deleting bookmark {bookmark_id} for user {user_id}")

    tokens = await get_valid_tokens(str(user_id), db)
    access_token = tokens.get("access_token")

    if not access_token or not x_id:
        raise BadRequest("Missing credentials for X API")

    try:
        await twitter_service.delete_bookmark(
            access_token=access_token,
            user_id=str(user_id),
            x_id=int(x_id),
            tweet_id=bookmark_id,
        )
        logger.info(f"Successfully deleted bookmark {bookmark_id} from X API")
    except Exception as e:
        logger.error(f"Failed to delete bookmark {bookmark_id} from X API: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete from X: {str(e)}. Local record preserved.",
        )

    await bookmark_service.delete_bookmark(db, str(user_id), bookmark_id)
    logger.info(f"Successfully deleted bookmark {bookmark_id} from local DB")

    return {"status": "deleted", "bookmark_id": bookmark_id}


@bookmark_router.patch("/{bookmark_id}/read")
async def mark_as_read(
    bookmark_id: str,
    request: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Mark a bookmark as read or unread."""
    user_id = current_user.id

    if request.is_read:
        await bookmark_service.mark_as_read(db, user_id, bookmark_id)
    else:
        await bookmark_service.mark_as_unread(db, user_id, bookmark_id)

    return {"status": "updated", "bookmark_id": bookmark_id, "is_read": request.is_read}


@bookmark_router.post("/{bookmark_id}/folders")
async def add_bookmark_to_folder(
    bookmark_id: str,
    request: BookmarkFolderRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Add a bookmark to a folder."""
    from uuid import UUID

    user_id = current_user.id
    folder_uuid = UUID(request.folder_id)
    await bookmark_service.add_bookmark_to_folder(db, user_id, bookmark_id, folder_uuid)
    return {
        "status": "added",
        "bookmark_id": bookmark_id,
        "folder_id": request.folder_id,
    }


@bookmark_router.delete("/{bookmark_id}/folders/{folder_id}")
async def remove_bookmark_from_folder(
    bookmark_id: str,
    folder_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Remove a bookmark from a folder."""
    from uuid import UUID

    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    await bookmark_service.remove_bookmark_from_folder(
        db, user_id, bookmark_id, folder_uuid
    )
    return {"status": "removed", "bookmark_id": bookmark_id, "folder_id": folder_id}


@bookmark_router.get("/{bookmark_id}/folders")
async def get_bookmark_folders(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Get folders containing a bookmark."""
    user_id = current_user.id
    folders = await bookmark_service.get_bookmark_folders(db, user_id, bookmark_id)
    return folders


@bookmark_router.post("/{bookmark_id}/tags")
async def add_tag_to_bookmark(
    bookmark_id: str,
    request: BookmarkTagRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Add a tag to a bookmark."""
    from uuid import UUID

    user_id = current_user.id
    tag_uuid = UUID(request.tag_id)
    await bookmark_service.add_tag_to_bookmark(db, user_id, bookmark_id, tag_uuid)
    return {"status": "added", "bookmark_id": bookmark_id, "tag_id": request.tag_id}


@bookmark_router.delete("/{bookmark_id}/tags/{tag_id}")
async def remove_tag_from_bookmark(
    bookmark_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Remove a tag from a bookmark."""
    from uuid import UUID

    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    await bookmark_service.remove_tag_from_bookmark(db, user_id, bookmark_id, tag_uuid)
    return {"status": "removed", "bookmark_id": bookmark_id, "tag_id": tag_id}


@bookmark_router.get("/{bookmark_id}/tags")
async def get_bookmark_tags(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Get tags for a bookmark."""
    user_id = current_user.id
    tags = await bookmark_service.get_bookmark_tags(db, user_id, bookmark_id)
    return tags
