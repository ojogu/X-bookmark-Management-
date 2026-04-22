from typing import Any, Dict, List
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.bookmark import Folder as FolderModel, bookmark_folders
from src.v1.base.exception import NotFoundError, AlreadyExistsError

from src.utils.log import get_logger

logger = get_logger(__name__)


class FolderService:
    async def get_folders(
        self, db: AsyncSession, user_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all folders for a user with bookmark count.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID

        Returns:
            List of folder objects with bookmark count
        """
        logger.info(f"Fetching folders for user_id={user_id}")

        result = await db.execute(
            sa.select(FolderModel).where(FolderModel.user_id == user_id)
        )
        folders = result.scalars().all()

        folder_list = []
        for folder in folders:
            count_result = await db.execute(
                sa.select(sa.func.count(bookmark_folders.c.bookmark_id)).where(
                    bookmark_folders.c.folder_id == folder.id
                )
            )
            bookmark_count = count_result.scalar() or 0

            folder_list.append(
                {
                    "id": str(folder.id),
                    "name": folder.name,
                    "bookmarkCount": bookmark_count,
                }
            )

        logger.info(f"Found {len(folder_list)} folders for user_id={user_id}")
        return folder_list

    async def create_folder(
        self, db: AsyncSession, user_id: UUID, name: str
    ) -> Dict[str, Any]:
        """
        Create a new folder for a user.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            name: Folder name

        Returns:
            Created folder object
        """
        logger.info(f"Creating folder '{name}' for user_id={user_id}")

        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.user_id == user_id, FolderModel.name == name
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsError(f"Folder '{name}' already exists")

        folder = FolderModel(user_id=user_id, name=name)
        db.add(folder)
        await db.flush()
        await db.refresh(folder)

        logger.info(f"Created folder '{name}' with id={folder.id}")
        return {
            "id": str(folder.id),
            "name": folder.name,
            "bookmarkCount": 0,
        }

    async def update_folder(
        self, db: AsyncSession, user_id: UUID, folder_id: UUID, name: str
    ) -> Dict[str, Any]:
        """
        Rename a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            folder_id: The folder's ID
            name: New folder name

        Returns:
            Updated folder object
        """
        logger.info(f"Updating folder {folder_id} for user_id={user_id}")

        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.id == folder_id, FolderModel.user_id == user_id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError(f"Folder not found")

        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.user_id == user_id,
                FolderModel.name == name,
                FolderModel.id != folder_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsError(f"Folder '{name}' already exists")

        folder.name = name
        await db.flush()
        await db.refresh(folder)

        count_result = await db.execute(
            sa.select(sa.func.count(bookmark_folders.c.bookmark_id)).where(
                bookmark_folders.c.folder_id == folder.id
            )
        )
        bookmark_count = count_result.scalar() or 0

        logger.info(f"Updated folder {folder_id} to name '{name}'")
        return {
            "id": str(folder.id),
            "name": folder.name,
            "bookmarkCount": bookmark_count,
        }

    async def delete_folder(
        self, db: AsyncSession, user_id: UUID, folder_id: UUID
    ) -> bool:
        """
        Delete a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            folder_id: The folder's ID

        Returns:
            True if deleted
        """
        logger.info(f"Deleting folder {folder_id} for user_id={user_id}")

        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.id == folder_id, FolderModel.user_id == user_id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError(f"Folder not found")

        await db.delete(folder)
        await db.commit()

        logger.info(f"Deleted folder {folder_id}")
        return True

    async def get_folder(
        self, db: AsyncSession, user_id: UUID, folder_id: UUID
    ) -> Dict[str, Any]:
        """
        Get a single folder by ID with bookmark count.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            folder_id: The folder's ID

        Returns:
            Folder object with bookmark count
        """
        logger.info(f"Fetching folder {folder_id} for user_id={user_id}")

        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.id == folder_id, FolderModel.user_id == user_id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError(f"Folder not found")

        count_result = await db.execute(
            sa.select(sa.func.count(bookmark_folders.c.bookmark_id)).where(
                bookmark_folders.c.folder_id == folder.id
            )
        )
        bookmark_count = count_result.scalar() or 0

        logger.info(f"Found folder {folder_id} with {bookmark_count} bookmarks")
        return {
            "id": str(folder.id),
            "name": folder.name,
            "bookmarkCount": bookmark_count,
        }
