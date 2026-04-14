from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.folder import FolderService
from src.v1.route.dependencies import get_current_user, get_folder_service
from pydantic import BaseModel
from uuid import UUID

logger = get_logger(__name__)

folder_router = APIRouter(prefix="/folders", tags=["folders"])


class CreateFolderRequest(BaseModel):
    name: str


class UpdateFolderRequest(BaseModel):
    name: str


@folder_router.get("")
async def get_folders(
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
    db: AsyncSession = Depends(get_session),
):
    """Get all folders for the current user."""
    user_id = current_user.id
    folders = await folder_service.get_folders(db, user_id)
    return folders


@folder_router.post("")
async def create_folder(
    request: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
    db: AsyncSession = Depends(get_session),
):
    """Create a new folder."""
    user_id = current_user.id
    folder = await folder_service.create_folder(db, user_id, request.name)
    return folder


@folder_router.put("/{folder_id}")
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
    db: AsyncSession = Depends(get_session),
):
    """Rename a folder."""
    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    folder = await folder_service.update_folder(db, user_id, folder_uuid, request.name)
    return folder


@folder_router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
    db: AsyncSession = Depends(get_session),
):
    """Delete a folder."""
    user_id = current_user.id
    folder_uuid = UUID(folder_id)
    await folder_service.delete_folder(db, user_id, folder_uuid)
    return {"status": "deleted", "folder_id": folder_id}
