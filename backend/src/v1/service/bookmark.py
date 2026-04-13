from typing import Any, Dict, List, Optional
from uuid import UUID
from .utils import _clean_structure, read_json_file

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from src.v1.service.user import UserService
from datetime import datetime, timedelta, timezone
from src.v1.schemas.bookmark import (
    BookmarkResponse,
    Author,
    Meta,
    Metrics,
    Post,
    Bookmark,
)
from src.v1.model import (
    Author as AuthorModel,
    Post as PostModel,
    Bookmark as BookmarkModel,
)

# from src.v1.service.twitter import twitter_service
from src.v1.base.exception import (
    Environment_Variable_Exception,
    InUseError,
    TokenExpired,
    NotFoundError,
    AlreadyExistsError,
    InvalidEmailPassword,
    BadRequest,
    NotVerified,
    EmailVerificationError,
    ServerError,
    NotActive,
    BaseExceptionClass,
)


from src.utils.log import get_logger

logger = get_logger(__name__)


class BookmarkService:
    def __init__(self, user_service: UserService = None):
        self.user_service = user_service

    async def check_if_author_exists(self, db: AsyncSession, author_id):
        result = await db.execute(
            sa.select(AuthorModel).where(author_id == AuthorModel.author_id_from_x)
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def check_if_post_exists(self, db: AsyncSession, post_id):
        result = await db.execute(
            sa.select(PostModel).where(post_id == PostModel.post_id)
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def check_if_bookmark_exists(self, db: AsyncSession, post_id, user_id):
        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.post_id == post_id, BookmarkModel.user_id == user_id
            )
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def fetch_next_token(self, db: AsyncSession, user_id):
        """Fetch the next_token for backfill pagination."""
        next_token = await db.execute(
            sa.select(BookmarkModel.next_token).where(user_id == BookmarkModel.user_id)
        )
        if not next_token:
            return None
        return next_token.scalar_one_or_none()

    async def get_last_sync_time(self, db: AsyncSession, user_id):
        """Get the last successful front sync timestamp for a user."""
        result = await db.execute(
            sa.select(User.last_front_sync_time).where(user_id == User.id)
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def update_last_sync_time(
        self, db: AsyncSession, user_id, sync_time: datetime
    ):
        """Update the last sync time after successful front sync."""
        await db.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(last_front_sync_time=sync_time)
        )
        await db.commit()

    async def count_user_bookmarks(self, db: AsyncSession, user_id: UUID) -> int:
        """Count total bookmarks for a user."""
        result = await db.execute(
            sa.select(sa.func.count(BookmarkModel.user_id)).where(
                BookmarkModel.user_id == user_id
            )
        )
        count = result.scalar()
        return count if count else 0

    async def get_bookmarks_from_db(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        sort: str = "date-desc",
        tag_ids: list = None,
        folder_id: Optional[str] = None,
        unread: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Fetch bookmarks from database with pagination.
        Returns data in X API response format for consistency.

        Args:
            db: SQLAlchemy session
            user_id: UUID of the user
            limit: Number of results to return
            offset: Offset for pagination
            search: Full-text search (post text, author name)
            sort: Sort order (date-desc, date-asc, alpha-asc, alpha-desc)
            tag_ids: Filter by tag IDs
            folder_id: Filter by folder ID
            unread: Filter only unread bookmarks

        Returns:
            Dict with 'data', 'includes', 'meta' keys matching X API response format
        """
        from src.v1.model.bookmark import (
            Bookmark as BookmarkModel,
            Folder as FolderModel,
            bookmark_folders,
        )
        from src.v1.model.post import Post as PostModel
        from src.v1.model.author import Author as AuthorModel

        logger.info(
            f"Fetching bookmarks from DB for user_id={user_id}, limit={limit}, offset={offset}, "
            f"search={search}, sort={sort}, tag_ids={tag_ids}, folder_id={folder_id}, unread={unread}"
        )

        # Build query with filters
        query = (
            sa.select(BookmarkModel, PostModel, AuthorModel)
            .join(PostModel, BookmarkModel.post_id == PostModel.id)
            .join(AuthorModel, PostModel.author_id == AuthorModel.id)
            .where(BookmarkModel.user_id == user_id)
        )

        # Apply search filter (post text or author name)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                sa.or_(
                    PostModel.text.ilike(search_pattern),
                    AuthorModel.name.ilike(search_pattern),
                    AuthorModel.username.ilike(search_pattern),
                )
            )

        # Apply unread filter
        if unread is True:
            query = query.where(BookmarkModel.is_read == False)

        # Apply folder filter
        if folder_id:
            folder_uuid = UUID(folder_id)
            query = query.join(
                bookmark_folders,
                BookmarkModel.post_id == bookmark_folders.c.bookmark_id,
            ).where(bookmark_folders.c.folder_id == folder_uuid)

        # Apply sorting
        if sort == "date-asc":
            query = query.order_by(PostModel.created_at_from_twitter.asc())
        elif sort == "alpha-asc":
            query = query.order_by(PostModel.text.asc())
        elif sort == "alpha-desc":
            query = query.order_by(PostModel.text.desc())
        else:  # date-desc (default)
            query = query.order_by(PostModel.created_at_from_twitter.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            logger.info(f"No bookmarks found for user_id={user_id}")
            return {"data": [], "includes": {"users": []}, "meta": {"result_count": 0}}

        data = []
        users_map = {}

        for bookmark, post, author in rows:
            author_x_id = author.author_id_from_x
            if author_x_id not in users_map:
                users_map[author_x_id] = {
                    "id": author_x_id,
                    "username": author.username,
                    "name": author.name,
                    "profile_image_url": author.profile_image_url,
                }

            data.append(
                {
                    "id": post.post_id,
                    "text": post.text,
                    "author_id": author_x_id,
                    "created_at": (
                        post.created_at_from_twitter.isoformat()
                        if post.created_at_from_twitter
                        else None
                    ),
                    "public_metrics": {
                        "retweet_count": 0,
                        "reply_count": 0,
                        "like_count": 0,
                        "quote_count": 0,
                        "bookmark_count": 0,
                        "impression_count": 0,
                    },
                    "lang": post.lang,
                    "possibly_sensitive": post.possibly_sensitive,
                }
            )

        # Get total count (without pagination limits for accurate count)
        count_query = sa.select(sa.func.count(BookmarkModel.user_id)).where(
            BookmarkModel.user_id == user_id
        )
        if search:
            search_pattern = f"%{search}%"
            count_query = (
                count_query.join(PostModel, BookmarkModel.post_id == PostModel.id)
                .join(AuthorModel, PostModel.author_id == AuthorModel.id)
                .where(
                    sa.or_(
                        PostModel.text.ilike(search_pattern),
                        AuthorModel.name.ilike(search_pattern),
                        AuthorModel.username.ilike(search_pattern),
                    )
                )
            )
        if unread is True:
            count_query = count_query.where(BookmarkModel.is_read == False)

        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        has_next = (offset + limit) < total_count

        response = {
            "data": data,
            "includes": {"users": list(users_map.values())},
            "meta": {
                "result_count": len(data),
                "total_count": total_count,
                "next_token": str(offset + limit) if has_next else None,
            },
        }

        logger.info(
            f"Retrieved {len(data)} bookmarks from DB for user_id={user_id}, total={total_count}"
        )
        return response

    async def save_bookmarks(
        self,
        db: AsyncSession,
        user_id: str,
        api_response: Dict[str, Any],
        next_token: Optional[str] = None,
        sync_time: Optional[datetime] = None,
    ):
        """
        Full pipeline to parse Twitter bookmarks API response and save to DB.

        Args:
            db: SQLAlchemy db object
            user_id: ID of the user whose bookmarks these are
            api_response: Raw JSON response from Twitter API
            next_token: Pagination token for backfill operations
            sync_time: Timestamp to update last_front_sync_time
        """
        logger.info(f"Starting bookmark save pipeline for user_id={user_id}")

        # Check if user exists
        logger.debug(f"Checking if user {user_id} exists")
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            raise NotFoundError(f"user: {user_id} does not exists")

        # Parse & validate API response using Pydantic
        logger.debug(f"Parsing API response for user {user_id}")
        validated_response = BookmarkService.parse_bookmarks_response(
            api_response, user_id
        )
        logger.info(
            f"Found {len(validated_response.bookmarks)} bookmarks to process for user {user_id}"
        )

        # Iterate through bookmarks and upsert data
        for index, bm in enumerate(validated_response.bookmarks, 1):
            logger.debug(
                f"Processing bookmark {index}/{len(validated_response.bookmarks)}"
            )
            post_data = (
                bm.post.model_dump()
                if hasattr(bm, "post")
                else bm.model_dump().get("post")
            )
            author_data = (
                bm.author.model_dump()
                if hasattr(bm, "author")
                else bm.model_dump().get("author")
            )

            # ---- Handle Author ----
            logger.debug(f"Checking author {author_data['id']}")
            author = await self.check_if_author_exists(db, author_data["id"])
            if not author:
                logger.debug(f"Creating new author record for {author_data['id']}")
                author = AuthorModel(
                    username=author_data.get("username", ""),
                    name=author_data.get("name", ""),
                    profile_image_url=str(author_data.get("profile_image_url", "")),
                    author_id_from_x=author_data.get("id", ""),
                )
                db.add(author)
                await db.flush()

            # ---- Handle Post ----
            logger.debug(f"Checking post {post_data['id']}")
            post = await self.check_if_post_exists(db, post_data["id"])
            if not post:
                logger.debug(f"Creating new post record for {post_data['id']}")
                post = PostModel(
                    post_id=post_data.get("id", ""),
                    text=post_data.get("text", ""),
                    created_at_from_twitter=post_data.get("created_at"),
                    lang=post_data.get("lang", ""),
                    possibly_sensitive=post_data.get("possibly_sensitive", False),
                    author_id=author.id,
                )
                db.add(post)
                await db.flush()

            # ---- Handle Bookmark ----
            logger.debug(
                f"Checking if bookmark exists for post {post.id} and user {user_id}"
            )
            existing_bm = await self.check_if_bookmark_exists(
                db, post_id=post.id, user_id=user_id
            )

            if not existing_bm:
                logger.debug(f"Creating new bookmark for post {post.id}")
                bookmark = BookmarkModel(
                    user_id=user_id,
                    post_id=post.id,
                    front_sync_token=next_token
                    if sync_time
                    else None,  # Use front_sync_token for front sync operations
                    next_token=next_token
                    or "",  # Set default empty string for front sync, actual token for backfill
                )
                db.add(bookmark)

        # Update user's last sync time if provided
        if sync_time:
            logger.debug(
                f"Updating last_front_sync_time for user {user_id} to {sync_time}"
            )
            await db.execute(
                sa.update(User)
                .where(User.id == user_id)
                .values(last_front_sync_time=sync_time)
            )

        # Commit all changes
        try:
            await db.commit()
            logger.info(
                f"Successfully saved all {len(validated_response.bookmarks)} bookmarks for user_id={user_id}"
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to save bookmarks for user_id={user_id}: {str(e)}",
                exc_info=True,
            )
            raise

    @staticmethod
    def parse_bookmarks_response(
        response: Dict[str, Any], user_id: str
    ) -> BookmarkResponse:
        """
        Parse Twitter bookmarks API response into structured BookmarkResponse.
        Ensures safe defaults and joins tweet data with author data.

        Args:
            response: raw API response
            user_id: ID of the user fetching bookmarks

        Returns:
            BookmarkResponse Pydantic model with validated and cleaned data.
        """
        logger.info(f"bookmark data: {response}")
        logger.info(f"Parsing bookmarks for user_id={user_id}")
        if isinstance(response, dict):
            tweets_data = response.get("data", [])
        elif isinstance(response, list):
            tweets_data = response

        authors_map = {
            u["id"]: u for u in response.get("includes", {}).get("users", []) or []
        }
        meta = response.get("meta", {}) or {}

        bookmarks_list = []

        for tweet in tweets_data:
            if not tweet:
                continue

            author_data = authors_map.get(tweet.get("author_id"), {}) or {}
            author = Author(
                id=author_data.get("id", ""),
                username=author_data.get("username", ""),
                name=author_data.get("name", ""),
                profile_image_url=author_data.get("profile_image_url", None),
            )

            metrics_data = tweet.get("public_metrics", {}) or {}
            metrics = Metrics(
                retweet_count=metrics_data.get("retweet_count", 0),
                reply_count=metrics_data.get("reply_count", 0),
                like_count=metrics_data.get("like_count", 0),
                quote_count=metrics_data.get("quote_count", 0),
                bookmark_count=metrics_data.get("bookmark_count", 0),
                impression_count=metrics_data.get("impression_count", 0),
            )

            post = Post(
                id=tweet.get("id", ""),
                text=tweet.get("text", ""),
                author_id=tweet.get("author_id", ""),
                created_at=tweet.get("created_at"),
                metrics=metrics,
                lang=tweet.get("lang", ""),
                possibly_sensitive=tweet.get("possibly_sensitive", False),
            )

            bookmark = Bookmark(internal_id=str(user_id), post=post, author=author)

            bookmarks_list.append(bookmark)

        structured_data = {
            "bookmarks": bookmarks_list,
            "meta": Meta(
                result_count=meta.get("result_count", len(bookmarks_list)),
                next_token=meta.get("next_token"),
            ),
        }

        cleaned_data = _clean_structure(structured_data)

        validated_response = BookmarkResponse(**cleaned_data)

        logger.info(
            f"Parsed {len(validated_response.bookmarks)} bookmarks for user_id={user_id}"
        )
        return validated_response

    async def delete_bookmark(
        self, db: AsyncSession, user_id: str, tweet_id: str
    ) -> bool:
        """
        Delete a bookmark from the local database.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID (UUID as string)
            tweet_id: The tweet/post ID to delete

        Returns:
            True if deleted, False if not found
        """
        from src.v1.model.post import Post as PostModel

        logger.info(f"Deleting bookmark for user_id={user_id}, tweet_id={tweet_id}")

        # First, find the post by tweet_id
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

        # Now delete the bookmark using composite key
        user_uuid = UUID(user_id)
        result = await db.execute(
            sa.delete(BookmarkModel).where(
                BookmarkModel.user_id == user_uuid, BookmarkModel.post_id == post.id
            )
        )

        await db.commit()

        if result.rowcount > 0:
            logger.info(
                f"Successfully deleted bookmark for user_id={user_id}, tweet_id={tweet_id}"
            )
            return True
        else:
            logger.warning(
                f"No bookmark found to delete for user_id={user_id}, tweet_id={tweet_id}"
            )
            return False

    # --------------------------------------------------------------
    # Folder methods
    # --------------------------------------------------------------
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
        from src.v1.model.bookmark import Folder as FolderModel, bookmark_folders

        logger.info(f"Fetching folders for user_id={user_id}")

        # Get folders with bookmark counts
        result = await db.execute(
            sa.select(FolderModel).where(FolderModel.user_id == user_id)
        )
        folders = result.scalars().all()

        folder_list = []
        for folder in folders:
            # Count bookmarks in this folder
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
        from src.v1.model.bookmark import Folder as FolderModel

        logger.info(f"Creating folder '{name}' for user_id={user_id}")

        # Check if folder with same name already exists
        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.user_id == user_id, FolderModel.name == name
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsError(f"Folder '{name}' already exists")

        # Create new folder
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
        from src.v1.model.bookmark import Folder as FolderModel

        logger.info(f"Updating folder {folder_id} for user_id={user_id}")

        # Find folder
        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.id == folder_id, FolderModel.user_id == user_id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError(f"Folder not found")

        # Check if new name already exists
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

        # Update name
        folder.name = name
        await db.flush()
        await db.refresh(folder)

        # Get bookmark count
        from src.v1.model.bookmark import bookmark_folders

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
        from src.v1.model.bookmark import Folder as FolderModel

        logger.info(f"Deleting folder {folder_id} for user_id={user_id}")

        # Find folder
        result = await db.execute(
            sa.select(FolderModel).where(
                FolderModel.id == folder_id, FolderModel.user_id == user_id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError(f"Folder not found")

        # Delete folder (cascade will handle bookmark_folders)
        await db.delete(folder)
        await db.commit()

        logger.info(f"Deleted folder {folder_id}")
        return True

    # --------------------------------------------------------------
    # Tag methods
    # --------------------------------------------------------------
    async def get_tags(self, db: AsyncSession, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all tags for a user with bookmark count.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID

        Returns:
            List of tag objects with bookmark count
        """
        from src.v1.model.tag import Tag as TagModel, bookmark_tags

        logger.info(f"Fetching tags for user_id={user_id}")

        # Get all tags
        result = await db.execute(
            sa.select(TagModel).where(TagModel.user_id == user_id)
        )
        tags = result.scalars().all()

        tag_list = []
        for tag in tags:
            # Count bookmarks with this tag
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
        self, db: AsyncSession, user_id: UUID, name: str, color: Optional[str] = None
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
        from src.v1.model.tag import Tag as TagModel

        logger.info(f"Creating tag '{name}' for user_id={user_id}")

        # Check if tag with same name already exists
        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.user_id == user_id, TagModel.name == name
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsError(f"Tag '{name}' already exists")

        # Create new tag
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
        color: Optional[str] = None,
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
        from src.v1.model.tag import Tag as TagModel, bookmark_tags

        logger.info(f"Updating tag {tag_id} for user_id={user_id}")

        # Find tag
        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError(f"Tag not found")

        # Only user-created tags can be edited
        if tag.source != "user":
            raise BadRequest("Cannot edit X annotation tags")

        # Check if new name already exists
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

        # Get bookmark count
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
        from src.v1.model.tag import Tag as TagModel

        logger.info(f"Deleting tag {tag_id} for user_id={user_id}")

        # Find tag
        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError(f"Tag not found")

        # Only user-created tags can be deleted
        if tag.source != "user":
            raise BadRequest("Cannot delete X annotation tags")

        # Delete tag (cascade will handle bookmark_tags)
        await db.delete(tag)
        await db.commit()

        logger.info(f"Deleted tag {tag_id}")
        return True

    # --------------------------------------------------------------
    # Mark as read methods
    # --------------------------------------------------------------
    async def mark_as_read(
        self, db: AsyncSession, user_id: UUID, tweet_id: str
    ) -> bool:
        """
        Mark a bookmark as read.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID

        Returns:
            True if marked, False if not found
        """
        from src.v1.model.post import Post as PostModel

        logger.info(f"Marking as read for user_id={user_id}, tweet_id={tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

        # Update bookmark is_read
        result = await db.execute(
            sa.update(BookmarkModel)
            .where(BookmarkModel.user_id == user_id, BookmarkModel.post_id == post.id)
            .values(is_read=True)
        )

        await db.commit()

        if result.rowcount > 0:
            logger.info(f"Marked as read for user_id={user_id}, tweet_id={tweet_id}")
            return True
        else:
            logger.warning(
                f"No bookmark found to mark as read for user_id={user_id}, tweet_id={tweet_id}"
            )
            return False

    async def mark_as_unread(
        self, db: AsyncSession, user_id: UUID, tweet_id: str
    ) -> bool:
        """
        Mark a bookmark as unread.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID

        Returns:
            True if marked, False if not found
        """
        from src.v1.model.post import Post as PostModel

        logger.info(f"Marking as unread for user_id={user_id}, tweet_id={tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

        # Update bookmark is_read
        result = await db.execute(
            sa.update(BookmarkModel)
            .where(BookmarkModel.user_id == user_id, BookmarkModel.post_id == post.id)
            .values(is_read=False)
        )

        await db.commit()

        if result.rowcount > 0:
            logger.info(f"Marked as unread for user_id={user_id}, tweet_id={tweet_id}")
            return True
        else:
            logger.warning(
                f"No bookmark found to mark as unread for user_id={user_id}, tweet_id={tweet_id}"
            )
            return False

    # --------------------------------------------------------------
    # Bookmark folder methods
    # --------------------------------------------------------------
    async def add_bookmark_to_folder(
        self, db: AsyncSession, user_id: UUID, tweet_id: str, folder_id: UUID
    ) -> bool:
        """
        Add a bookmark to a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID
            folder_id: The folder's ID

        Returns:
            True if added
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.bookmark import bookmark_folders

        logger.info(f"Adding bookmark {tweet_id} to folder {folder_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            raise NotFoundError(f"Post not found")

        # Find the bookmark
        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.user_id == user_id, BookmarkModel.post_id == post.id
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise NotFoundError(f"Bookmark not found")

        # Check if already in folder
        result = await db.execute(
            sa.select(bookmark_folders).where(
                bookmark_folders.c.bookmark_id == bookmark.post_id,
                bookmark_folders.c.folder_id == folder_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Bookmark already in folder")
            return True

        # Add to folder
        await db.execute(
            bookmark_folders.insert().values(
                bookmark_id=bookmark.post_id, folder_id=folder_id
            )
        )
        await db.commit()

        logger.info(f"Added bookmark to folder")
        return True

    async def remove_bookmark_from_folder(
        self, db: AsyncSession, user_id: UUID, tweet_id: str, folder_id: UUID
    ) -> bool:
        """
        Remove a bookmark from a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID
            folder_id: The folder's ID

        Returns:
            True if removed
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.bookmark import bookmark_folders

        logger.info(f"Removing bookmark {tweet_id} from folder {folder_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            raise NotFoundError(f"Post not found")

        # Remove from folder
        await db.execute(
            bookmark_folders.delete().where(
                bookmark_folders.c.bookmark_id == post.id,
                bookmark_folders.c.folder_id == folder_id,
            )
        )
        await db.commit()

        logger.info(f"Removed bookmark from folder")
        return True

    async def get_bookmark_folders(
        self, db: AsyncSession, user_id: UUID, tweet_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get folders that contain a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID

        Returns:
            List of folder objects
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.bookmark import Folder as FolderModel, bookmark_folders

        logger.info(f"Getting folders for bookmark {tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            return []

        # Get folders containing this post
        result = await db.execute(
            sa.select(FolderModel)
            .join(bookmark_folders, FolderModel.id == bookmark_folders.c.folder_id)
            .where(bookmark_folders.c.bookmark_id == post.id)
        )
        folders = result.scalars().all()

        folder_list = []
        for folder in folders:
            folder_list.append(
                {
                    "id": str(folder.id),
                    "name": folder.name,
                }
            )

        return folder_list

    # --------------------------------------------------------------
    # Bookmark tag methods
    # --------------------------------------------------------------
    async def add_tag_to_bookmark(
        self, db: AsyncSession, user_id: UUID, tweet_id: str, tag_id: UUID
    ) -> bool:
        """
        Add a tag to a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID
            tag_id: The tag's ID

        Returns:
            True if added
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.tag import Tag as TagModel, bookmark_tags

        logger.info(f"Adding tag {tag_id} to bookmark {tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            raise NotFoundError(f"Post not found")

        # Verify tag exists and belongs to user
        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError(f"Tag not found")

        # Check if already tagged
        result = await db.execute(
            sa.select(bookmark_tags).where(
                bookmark_tags.c.bookmark_id == post.id, bookmark_tags.c.tag_id == tag_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Bookmark already tagged")
            return True

        # Add tag
        await db.execute(
            bookmark_tags.insert().values(bookmark_id=post.id, tag_id=tag_id)
        )
        await db.commit()

        logger.info(f"Added tag to bookmark")
        return True

    async def remove_tag_from_bookmark(
        self, db: AsyncSession, user_id: UUID, tweet_id: str, tag_id: UUID
    ) -> bool:
        """
        Remove a tag from a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID
            tag_id: The tag's ID

        Returns:
            True if removed
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.tag import Tag as TagModel, bookmark_tags

        logger.info(f"Removing tag {tag_id} from bookmark {tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            raise NotFoundError(f"Post not found")

        # Verify tag belongs to user
        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError(f"Tag not found")

        # Remove tag
        await db.execute(
            bookmark_tags.delete().where(
                bookmark_tags.c.bookmark_id == post.id, bookmark_tags.c.tag_id == tag_id
            )
        )
        await db.commit()

        logger.info(f"Removed tag from bookmark")
        return True

    async def get_bookmark_tags(
        self, db: AsyncSession, user_id: UUID, tweet_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tags for a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            tweet_id: The tweet/post ID

        Returns:
            List of tag objects
        """
        from src.v1.model.post import Post as PostModel
        from src.v1.model.tag import Tag as TagModel, bookmark_tags

        logger.info(f"Getting tags for bookmark {tweet_id}")

        # Find the post
        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            return []

        # Get tags
        result = await db.execute(
            sa.select(TagModel)
            .join(bookmark_tags, TagModel.id == bookmark_tags.c.tag_id)
            .where(bookmark_tags.c.bookmark_id == post.id)
        )
        tags = result.scalars().all()

        tag_list = []
        for tag in tags:
            tag_list.append(
                {
                    "id": str(tag.id),
                    "name": tag.name,
                    "color": tag.color,
                }
            )

        return tag_list
