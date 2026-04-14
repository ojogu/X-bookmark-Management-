from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
from src.v1.service.bookmark import BookmarkService
from src.v1.service.user import UserService
from src.v1.route.dependencies import get_current_user, get_bookmark_service
from src.v1.base.exception import BadRequest
from src.celery.task import front_sync_bookmark_task
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

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
#
# Query Parameters:
#   - limit: Number of results (default 20)
#   - offset: Pagination offset (default 0)
#   - search: Full-text search (post text, author name)
#   - sort: Sort order (date-desc, date-asc, alpha-asc, alpha-desc)
#   - tags: Comma-separated tag IDs to filter by
#   - folder_id: Filter by folder ID
#   - unread: Filter only unread bookmarks
# --------------------------------------------------------------
@client_router.get("/bookmarks")
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
    # Get current user's ID from auth token
    user_id = current_user.id

    # Parse filter params
    tag_ids = tags.split(",") if tags else []

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

        # Return from DB (applies limit/offset pagination + search/sort/filter)
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

    # --------------------------------------------------------------
    # Case 2: DB has data -> Return from DB with pagination
    # --------------------------------------------------------------
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


# --------------------------------------------------------------
# DELETE /client/bookmarks/{id}
# --------------------------------------------------------------
# Delete a bookmark from both SaveStack DB and X API.
# X API is source of truth - if X API fails, abort and keep local record.
# --------------------------------------------------------------
@client_router.delete("/bookmarks/{bookmark_id}")
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

    # Get valid OAuth tokens for X API calls
    tokens = await get_valid_tokens(str(user_id), db)
    access_token = tokens.get("access_token")

    # Validate we have required credentials
    if not access_token or not x_id:
        raise BadRequest("Missing credentials for X API")

    # Try to delete from X API first (source of truth)
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
        # X API failed - abort and keep local record
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete from X: {str(e)}. Local record preserved.",
        )
    #TODO: handle delete from X directly in req-res cycle, move to queue
    # X API succeeded - now delete from local DB
    await bookmark_service.delete_bookmark(db, str(user_id), bookmark_id)
    logger.info(f"Successfully deleted bookmark {bookmark_id} from local DB")

    return {"status": "deleted", "bookmark_id": bookmark_id}


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


# --------------------------------------------------------------
# GET /client/folders
# --------------------------------------------------------------
# Get all folders for the current user with bookmark counts.
# --------------------------------------------------------------
@client_router.get("/folders")
async def get_folders(
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Get all folders for the current user."""
    user_id = current_user.id
    folders = await bookmark_service.get_folders(db, user_id)
    return folders


# --------------------------------------------------------------
# POST /client/folders
# --------------------------------------------------------------
# Create a new folder for the current user.
# --------------------------------------------------------------


class CreateFolderRequest(BaseModel):
    name: str


@client_router.post("/folders")
async def create_folder(
    request: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Create a new folder."""
    user_id = current_user.id
    folder = await bookmark_service.create_folder(db, user_id, request.name)
    return folder


# --------------------------------------------------------------
# PUT /client/folders/{folder_id}
# --------------------------------------------------------------
# Rename a folder.
# --------------------------------------------------------------
class UpdateFolderRequest(BaseModel):
    name: str


@client_router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Rename a folder."""
    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    folder = await bookmark_service.update_folder(
        db, user_id, folder_uuid, request.name
    )
    return folder


# --------------------------------------------------------------
# DELETE /client/folders/{folder_id}
# --------------------------------------------------------------
# Delete a folder.
# --------------------------------------------------------------
@client_router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Delete a folder."""
    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    await bookmark_service.delete_folder(db, user_id, folder_uuid)
    return {"status": "deleted", "folder_id": folder_id}


# --------------------------------------------------------------
# GET /client/tags
# --------------------------------------------------------------
# Get all tags for the current user with bookmark counts.
# --------------------------------------------------------------
@client_router.get("/tags")
async def get_tags(
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Get all tags for the current user."""
    user_id = current_user.id
    tags = await bookmark_service.get_tags(db, user_id)
    return tags


# --------------------------------------------------------------
# POST /client/tags
# --------------------------------------------------------------
# Create a new tag for the current user.
# --------------------------------------------------------------
class CreateTagRequest(BaseModel):
    name: str
    color: Optional[str] = None


@client_router.post("/tags")
async def create_tag(
    request: CreateTagRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Create a new tag."""
    user_id = current_user.id
    tag = await bookmark_service.create_tag(db, user_id, request.name, request.color)
    return tag


# --------------------------------------------------------------
# PUT /client/tags/{tag_id}
# --------------------------------------------------------------
# Update a tag (name and/or color).
# --------------------------------------------------------------
class UpdateTagRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


@client_router.put("/tags/{tag_id}")
async def update_tag(
    tag_id: str,
    request: UpdateTagRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Update a tag."""
    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    name = request.name or ""
    tag = await bookmark_service.update_tag(db, user_id, tag_uuid, name, request.color)
    return tag


# --------------------------------------------------------------
# DELETE /client/tags/{tag_id}
# --------------------------------------------------------------
# Delete a tag.
# --------------------------------------------------------------
@client_router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Delete a tag."""
    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    await bookmark_service.delete_tag(db, user_id, tag_uuid)
    return {"status": "deleted", "tag_id": tag_id}


# --------------------------------------------------------------
# GET /client/user/info
# --------------------------------------------------------------
# Get current user profile info.
# --------------------------------------------------------------
@client_router.get("/user/info")
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get current user profile info."""
    user_service = UserService(db=db)
    user_info = await user_service.get_user_info(str(current_user.id))
    return user_info


# --------------------------------------------------------------
# PATCH /client/bookmarks/{bookmark_id}/read
# --------------------------------------------------------------
# Mark a bookmark as read or unread.
# --------------------------------------------------------------
class MarkReadRequest(BaseModel):
    is_read: bool


@client_router.patch("/bookmarks/{bookmark_id}/read")
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


# --------------------------------------------------------------
# POST /client/bookmarks/{bookmark_id}/folders
# --------------------------------------------------------------
# Add a bookmark to a folder.
# --------------------------------------------------------------
class BookmarkFolderRequest(BaseModel):
    folder_id: str


@client_router.post("/bookmarks/{bookmark_id}/folders")
async def add_bookmark_to_folder(
    bookmark_id: str,
    request: BookmarkFolderRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Add a bookmark to a folder."""
    user_id = current_user.id
    folder_uuid = UUID(request.folder_id)
    await bookmark_service.add_bookmark_to_folder(db, user_id, bookmark_id, folder_uuid)
    return {
        "status": "added",
        "bookmark_id": bookmark_id,
        "folder_id": request.folder_id,
    }


# --------------------------------------------------------------
# DELETE /client/bookmarks/{bookmark_id}/folders/{folder_id}
# --------------------------------------------------------------
# Remove a bookmark from a folder.
# --------------------------------------------------------------
@client_router.delete("/bookmarks/{bookmark_id}/folders/{folder_id}")
async def remove_bookmark_from_folder(
    bookmark_id: str,
    folder_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Remove a bookmark from a folder."""
    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    await bookmark_service.remove_bookmark_from_folder(
        db, user_id, bookmark_id, folder_uuid
    )
    return {"status": "removed", "bookmark_id": bookmark_id, "folder_id": folder_id}


# --------------------------------------------------------------
# GET /client/bookmarks/{bookmark_id}/folders
# --------------------------------------------------------------
# Get folders containing a bookmark.
# --------------------------------------------------------------
@client_router.get("/bookmarks/{bookmark_id}/folders")
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


# --------------------------------------------------------------
# POST /client/bookmarks/{bookmark_id}/tags
# --------------------------------------------------------------
# Add a tag to a bookmark.
# --------------------------------------------------------------
class BookmarkTagRequest(BaseModel):
    tag_id: str


@client_router.post("/bookmarks/{bookmark_id}/tags")
async def add_tag_to_bookmark(
    bookmark_id: str,
    request: BookmarkTagRequest,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Add a tag to a bookmark."""
    user_id = current_user.id
    tag_uuid = UUID(request.tag_id)
    await bookmark_service.add_tag_to_bookmark(db, user_id, bookmark_id, tag_uuid)
    return {"status": "added", "bookmark_id": bookmark_id, "tag_id": request.tag_id}


# --------------------------------------------------------------
# DELETE /client/bookmarks/{bookmark_id}/tags/{tag_id}
# --------------------------------------------------------------
# Remove a tag from a bookmark.
# --------------------------------------------------------------
@client_router.delete("/bookmarks/{bookmark_id}/tags/{tag_id}")
async def remove_tag_from_bookmark(
    bookmark_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):
    """Remove a tag from a bookmark."""
    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    await bookmark_service.remove_tag_from_bookmark(db, user_id, bookmark_id, tag_uuid)
    return {"status": "removed", "bookmark_id": bookmark_id, "tag_id": tag_id}


# --------------------------------------------------------------
# GET /client/bookmarks/{bookmark_id}/tags
# --------------------------------------------------------------
# Get tags for a bookmark.
# --------------------------------------------------------------
@client_router.get("/bookmarks/{bookmark_id}/tags")
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
