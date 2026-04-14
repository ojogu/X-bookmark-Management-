from typing import Any, Dict, List
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.tag import Tag as TagModel, bookmark_tags
from src.v1.model.bookmark import Bookmark as BookmarkModel
from src.v1.model.post import Post as PostModel
from src.v1.base.exception import NotFoundError, AlreadyExistsError, BadRequest

from src.utils.log import get_logger

logger = get_logger(__name__)


class TagService:
    async def get_tags(self, db: AsyncSession, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all tags for a user with bookmark count.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID

        Returns:
            List of tag objects with bookmark count
        """
        logger.info(f"Fetching tags for user_id={user_id}")

        result = await db.execute(
            sa.select(TagModel).where(TagModel.user_id == user_id)
        )
        tags = result.scalars().all()

        tag_list = []
        for tag in tags:
            count_result = await db.execute(
                sa.select(sa.func.count(bookmark_tags.c.bookmark_id)).where(
                    bookmark_tags.c.tag_id == tag.id
                )
            )
            bookmark_count = count_result.scalar() or 0

            tag_list.append(
                {
                    "id": str(tag.id),
                    "name": tag.name,
                    "color": tag.color,
                    "source": tag.source,
                    "bookmarkCount": bookmark_count,
                }
            )

        logger.info(f"Found {len(tag_list)} tags for user_id={user_id}")
        return tag_list

    async def create_tag(
        self, db: AsyncSession, user_id: UUID, name: str, color: str = None
    ) -> Dict[str, Any]:
        """
        Create a new tag for a user.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            name: Tag name
            color: Optional color hex code

        Returns:
            Created tag object
        """
        logger.info(f"Creating tag '{name}' for user_id={user_id}")

        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.user_id == user_id, TagModel.name == name
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsError(f"Tag '{name}' already exists")

        tag = TagModel(user_id=user_id, name=name, color=color, source="user")
        db.add(tag)
        await db.flush()
        await db.refresh(tag)

        logger.info(f"Created tag '{name}' with id={tag.id}")
        return {
            "id": str(tag.id),
            "name": tag.name,
            "color": tag.color,
            "source": tag.source,
            "bookmarkCount": 0,
        }

    async def update_tag(
        self,
        db: AsyncSession,
        user_id: UUID,
        tag_id: UUID,
        name: str,
        color: str = None,
    ) -> Dict[str, Any]:
        """
        Update a tag (name and/or color).

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tag_id: The tag's ID
            name: New tag name
            color: Optional new color

        Returns:
            Updated tag object
        """
        logger.info(f"Updating tag {tag_id} for user_id={user_id}")

        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError(f"Tag not found")

        if tag.source != "user":
            raise BadRequest("Cannot edit X annotation tags")

        if name and name != tag.name:
            result = await db.execute(
                sa.select(TagModel).where(
                    TagModel.user_id == user_id,
                    TagModel.name == name,
                    TagModel.id != tag_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise AlreadyExistsError(f"Tag '{name}' already exists")
            tag.name = name

        if color is not None:
            tag.color = color

        await db.flush()
        await db.refresh(tag)

        count_result = await db.execute(
            sa.select(sa.func.count(bookmark_tags.c.bookmark_id)).where(
                bookmark_tags.c.tag_id == tag.id
            )
        )
        bookmark_count = count_result.scalar() or 0

        logger.info(f"Updated tag {tag_id}")
        return {
            "id": str(tag.id),
            "name": tag.name,
            "color": tag.color,
            "source": tag.source,
            "bookmarkCount": bookmark_count,
        }

    async def delete_tag(self, db: AsyncSession, user_id: UUID, tag_id: UUID) -> bool:
        """
        Delete a tag.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tag_id: The tag's ID

        Returns:
            True if deleted
        """
        logger.info(f"Deleting tag {tag_id} for user_id={user_id}")

        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError(f"Tag not found")

        if tag.source != "user":
            raise BadRequest("Cannot delete X annotation tags")

        await db.delete(tag)
        await db.commit()

        logger.info(f"Deleted tag {tag_id}")
        return True
