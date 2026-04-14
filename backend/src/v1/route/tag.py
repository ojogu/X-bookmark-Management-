from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.tag import TagService
from src.v1.route.dependencies import get_current_user, get_tag_service
from src.v1.schemas import CreateTagRequest, UpdateTagRequest
from uuid import UUID

logger = get_logger(__name__)

tag_router = APIRouter(prefix="/tags", tags=["tags"])


@tag_router.get("")
async def get_tags(
    current_user: User = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
    db: AsyncSession = Depends(get_session),
):
    """Get all tags for the current user."""
    user_id = current_user.id
    tags = await tag_service.get_tags(db, user_id)
    return tags


@tag_router.post("")
async def create_tag(
    request: CreateTagRequest,
    current_user: User = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
    db: AsyncSession = Depends(get_session),
):
    """Create a new tag."""
    user_id = current_user.id
    tag = await tag_service.create_tag(db, user_id, request.name, request.color)
    return tag


@tag_router.put("/{tag_id}")
async def update_tag(
    tag_id: str,
    request: UpdateTagRequest,
    current_user: User = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
    db: AsyncSession = Depends(get_session),
):
    """Update a tag."""
    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    name = request.name or ""
    tag = await tag_service.update_tag(db, user_id, tag_uuid, name, request.color)
    return tag


@tag_router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
    db: AsyncSession = Depends(get_session),
):
    """Delete a tag."""
    user_id = current_user.id
    tag_uuid = UUID(tag_id)
    await tag_service.delete_tag(db, user_id, tag_uuid)
    return {"status": "deleted", "tag_id": tag_id}
