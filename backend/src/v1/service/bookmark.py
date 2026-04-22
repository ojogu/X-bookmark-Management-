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
from src.v1.schema.bookmark import (
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
    Folder as FolderModel,
    Tag as TagModel,
    bookmark_folders,
    bookmark_tags,
)

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
    def __init__(self, db: AsyncSession = None, user_service: UserService = None):
        self.db = db
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
        result = await db.execute(sa.select(User.next_token).where(User.id == user_id))
        if not result:
            return None
        return result.scalar_one_or_none()

    async def fetch_front_sync_token(self, db: AsyncSession, user_id):
        """Fetch the front_sync_token for front sync pagination."""
        result = await db.execute(
            sa.select(User.front_sync_token).where(User.id == user_id)
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def get_existing_post_ids(
        self, db: AsyncSession, user_id: UUID, post_ids: list
    ) -> set:
        """Bulk-check which post_ids exist in DB for a user. Returns set of existing post_ids."""
        if not post_ids:
            return set()

        result = await db.execute(
            sa.select(PostModel.post_id)
            .join(BookmarkModel, BookmarkModel.post_id == PostModel.id)
            .where(
                BookmarkModel.user_id == user_id,
                PostModel.post_id.in_(post_ids),
            )
        )
        return set(row[0] for row in result.fetchall())

    async def fetch_front_watermark_id(self, db: AsyncSession, user_id):
        """Fetch the front_watermark_id (newest bookmark seen) for cold start detection."""
        result = await db.execute(
            sa.select(User.front_watermark_id).where(User.id == user_id)
        )
        if not result:
            return None
        return result.scalar_one_or_none()

    async def update_front_watermark_id(
        self, db: AsyncSession, user_id, watermark_id: str
    ):
        """Update the front_watermark_id (newest bookmark seen)."""
        await db.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(front_watermark_id=watermark_id)
        )
        await db.commit()

    async def update_backfill_cursor(self, db: AsyncSession, user_id, cursor: str):
        """Update the backfill cursor (next_token) for backfill worker."""
        await db.execute(
            sa.update(User).where(User.id == user_id).values(next_token=cursor)
        )
        await db.commit()

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

    async def update_front_sync_token(self, db: AsyncSession, user_id, token: str):
        """Update the front_sync_token for front sync pagination."""
        await db.execute(
            sa.update(User).where(User.id == user_id).values(front_sync_token=token)
        )

    async def update_next_token(self, db: AsyncSession, user_id, token: str):
        """Update the next_token for backfill pagination."""
        await db.execute(
            sa.update(User).where(User.id == user_id).values(next_token=token)
        )

    async def mark_backfill_complete(self, db: AsyncSession, user_id):
        """Mark backfill as complete for a user."""
        await db.execute(
            sa.update(User).where(User.id == user_id).values(is_backfill_complete=True)
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
        limit: int = 10,
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
        logger.info(
            f"Fetching bookmarks from DB for user_id={user_id}, limit={limit}, offset={offset}, "
            f"search={search}, sort={sort}, tag_ids={tag_ids}, folder_id={folder_id}, unread={unread}"
        )

        query = (
            sa.select(BookmarkModel, PostModel, AuthorModel)
            .join(PostModel, BookmarkModel.post_id == PostModel.id)
            .outerjoin(AuthorModel, PostModel.author_id == AuthorModel.id)
            .where(BookmarkModel.user_id == user_id)
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                sa.or_(
                    PostModel.text.ilike(search_pattern),
                    sa.and_(
                        AuthorModel.name.isnot(None),
                        AuthorModel.name.ilike(search_pattern),
                    ),
                    sa.and_(
                        AuthorModel.username.isnot(None),
                        AuthorModel.username.ilike(search_pattern),
                    ),
                )
            )

        if unread is True:
            query = query.where(BookmarkModel.is_read == False)

        if folder_id:
            folder_uuid = UUID(folder_id)
            query = query.join(
                bookmark_folders,
                BookmarkModel.id == bookmark_folders.c.bookmark_id,
            ).where(bookmark_folders.c.folder_id == folder_uuid)

        if tag_ids:
            tag_uuids = [UUID(tid) for tid in tag_ids]
            query = query.join(
                bookmark_tags,
                BookmarkModel.id == bookmark_tags.c.bookmark_id,
            ).where(bookmark_tags.c.tag_id.in_(tag_uuids))

        if sort == "date-asc":
            query = query.order_by(PostModel.created_at_from_twitter.asc())
        elif sort == "alpha-asc":
            query = query.order_by(PostModel.text.asc())
        elif sort == "alpha-desc":
            query = query.order_by(PostModel.text.desc())
        else:
            query = query.order_by(PostModel.created_at_from_twitter.desc())

        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            logger.info(f"No bookmarks found for user_id={user_id}")
            return {"data": [], "includes": {"users": []}, "meta": {"result_count": 0}}

        bookmark_ids = [bookmark.id for bookmark, post, author in rows]

        tags_query = (
            sa.select(bookmark_tags.c.bookmark_id, TagModel)
            .join(TagModel, bookmark_tags.c.tag_id == TagModel.id)
            .where(bookmark_tags.c.bookmark_id.in_(bookmark_ids))
        )
        tags_result = await db.execute(tags_query)
        tags_rows = tags_result.all()

        bookmark_tags_map: Dict[str, List[Dict[str, Any]]] = {}
        for bookmark_id, tag in tags_rows:
            tag_dict = {
                "id": str(tag.id),
                "name": tag.name,
                "color": tag.color,
            }
            if str(bookmark_id) not in bookmark_tags_map:
                bookmark_tags_map[str(bookmark_id)] = []
            bookmark_tags_map[str(bookmark_id)].append(tag_dict)

        data = []
        users_map = {}

        for bookmark, post, author in rows:
            author_x_id = author.author_id_from_x if author else ""
            if author_x_id and author_x_id not in users_map:
                users_map[author_x_id] = {
                    "id": author_x_id,
                    "username": author.username if author else "",
                    "name": author.name if author else "",
                    "profile_image_url": author.profile_image_url if author else None,
                }

            data.append(
                {
                    "id": post.post_id,
                    "bookmark_id": str(bookmark.id),
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
                    "tags": bookmark_tags_map.get(str(bookmark.id), []),
                }
            )

        count_query = sa.select(sa.func.count(BookmarkModel.user_id)).where(
            BookmarkModel.user_id == user_id
        )
        if search:
            search_pattern = f"%{search}%"
            count_query = (
                count_query.join(PostModel, BookmarkModel.post_id == PostModel.id)
                .outerjoin(AuthorModel, PostModel.author_id == AuthorModel.id)
                .where(
                    sa.or_(
                        PostModel.text.ilike(search_pattern),
                        sa.and_(
                            AuthorModel.name.isnot(None),
                            AuthorModel.name.ilike(search_pattern),
                        ),
                        sa.and_(
                            AuthorModel.username.isnot(None),
                            AuthorModel.username.ilike(search_pattern),
                        ),
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

        logger.debug(f"Checking if user {user_id} exists")
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            raise NotFoundError(f"user: {user_id} does not exists")

        logger.debug(f"Parsing API response for user {user_id}")
        validated_response = BookmarkService.parse_bookmarks_response(
            api_response, user_id
        )
        logger.info(
            f"Found {len(validated_response.bookmarks)} bookmarks to process for user {user_id}"
        )

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
                if hasattr(bm, "author") and bm.author
                else bm.model_dump().get("author")
            )

            author_model = None
            if author_data and author_data.get("id"):
                logger.debug(f"Checking author {author_data['id']}")
                author_model = await self.check_if_author_exists(db, author_data["id"])
                if author_model:
                    logger.debug(f"Updating existing author {author_data['id']}")
                    author_model.username = (
                        author_data.get("username", "") or author_model.username
                    )
                    author_model.name = author_data.get("name", "") or author_model.name
                    author_model.profile_image_url = (
                        str(author_data.get("profile_image_url", ""))
                        or author_model.profile_image_url
                    )
                else:
                    logger.debug(f"Creating new author record for {author_data['id']}")
                    author_model = AuthorModel(
                        username=author_data.get("username", ""),
                        name=author_data.get("name", ""),
                        profile_image_url=str(author_data.get("profile_image_url", "")),
                        author_id_from_x=author_data.get("id", ""),
                    )
                    db.add(author_model)
                    await db.flush()
            else:
                logger.warning(
                    f"No author data for post {post_data.get('id')} — skipping author link"
                )

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
                    author_id=author_model.id if author_model else None,
                )
                db.add(post)
                await db.flush()

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
                )
                db.add(bookmark)
            # Don't store tokens on individual bookmarks anymore

        if sync_time:
            logger.debug(
                f"Updating front_sync_token and last_front_sync_time for user {user_id}"
            )
            await self.update_front_sync_token(db, user_id, next_token)
            await self.update_last_sync_time(db, user_id, sync_time)
        else:
            if next_token:
                logger.debug(f"Updating next_token for user {user_id}")
                await self.update_next_token(db, user_id, next_token)

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

            author_data = authors_map.get(
                tweet.get("author_id")
            )  # None if missing, not empty dict
            if author_data:
                author = Author(
                    id=author_data.get("id", ""),
                    username=author_data.get("username", ""),
                    name=author_data.get("name", ""),
                    profile_image_url=author_data.get("profile_image_url", None),
                )
            else:
                logger.warning(
                    f"No author data returned by X for author_id={tweet.get('author_id')} "
                    f"on post={tweet.get('id')} — saving post with null author"
                )
                author = None

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
        logger.info(f"Deleting bookmark for user_id={user_id}, tweet_id={tweet_id}")

        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

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
        logger.info(f"Marking as read for user_id={user_id}, tweet_id={tweet_id}")

        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

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
        logger.info(f"Marking as unread for user_id={user_id}, tweet_id={tweet_id}")

        result = await db.execute(
            sa.select(PostModel).where(PostModel.post_id == tweet_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post not found for tweet_id={tweet_id}")
            return False

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

    async def add_bookmark_to_folder(
        self, db: AsyncSession, user_id: UUID, bookmark_id: UUID, folder_id: UUID
    ) -> bool:
        """
        Add a bookmark to a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID
            folder_id: The folder's ID

        Returns:
            True if added
        """
        logger.info(f"Adding bookmark {bookmark_id} to folder {folder_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == bookmark_id,
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise NotFoundError(f"Bookmark not found")

        result = await db.execute(
            sa.select(bookmark_folders).where(
                bookmark_folders.c.bookmark_id == bookmark.id,
                bookmark_folders.c.folder_id == folder_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Bookmark already in folder")
            return True

        await db.execute(
            bookmark_folders.insert().values(
                bookmark_id=bookmark.id, folder_id=folder_id
            )
        )
        await db.commit()

        logger.info(f"Added bookmark to folder")
        return True

    async def remove_bookmark_from_folder(
        self, db: AsyncSession, user_id: UUID, bookmark_id: UUID, folder_id: UUID
    ) -> bool:
        """
        Remove a bookmark from a folder.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID
            folder_id: The folder's ID

        Returns:
            True if removed
        """
        logger.info(f"Removing bookmark {bookmark_id} from folder {folder_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == bookmark_id,
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise NotFoundError(f"Bookmark not found")

        await db.execute(
            bookmark_folders.delete().where(
                bookmark_folders.c.bookmark_id == bookmark.id,
                bookmark_folders.c.folder_id == folder_id,
            )
        )
        await db.commit()

        logger.info(f"Removed bookmark from folder")
        return True

    async def get_bookmark_folders(
        self, db: AsyncSession, user_id: UUID, bookmark_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get folders containing a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID

        Returns:
            List of folder objects
        """
        logger.info(f"Getting folders for bookmark {bookmark_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == UUID(bookmark_id),
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            return []

        result = await db.execute(
            sa.select(FolderModel)
            .join(bookmark_folders, FolderModel.id == bookmark_folders.c.folder_id)
            .where(bookmark_folders.c.bookmark_id == bookmark.id)
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

    async def add_tag_to_bookmark(
        self, db: AsyncSession, user_id: UUID, bookmark_id: UUID, tag_id: UUID
    ) -> bool:
        """
        Add a tag to a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID
            tag_id: The tag's ID

        Returns:
            True if added
        """
        logger.info(f"Adding tag {tag_id} to bookmark {bookmark_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == bookmark_id,
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise NotFoundError(f"Bookmark not found")

        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError(f"Tag not found")

        result = await db.execute(
            sa.select(bookmark_tags).where(
                bookmark_tags.c.bookmark_id == bookmark.id,
                bookmark_tags.c.tag_id == tag_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Bookmark already tagged")
            return True

        await db.execute(
            bookmark_tags.insert().values(bookmark_id=bookmark.id, tag_id=tag_id)
        )
        await db.commit()

        logger.info(f"Added tag to bookmark")
        return True

    async def remove_tag_from_bookmark(
        self, db: AsyncSession, user_id: UUID, bookmark_id: UUID, tag_id: UUID
    ) -> bool:
        """
        Remove a tag from a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID
            tag_id: The tag's ID

        Returns:
            True if removed
        """
        logger.info(f"Removing tag {tag_id} from bookmark {bookmark_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == bookmark_id,
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise NotFoundError(f"Bookmark not found")

        result = await db.execute(
            sa.select(TagModel).where(
                TagModel.id == tag_id, TagModel.user_id == user_id
            )
        )
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError(f"Tag not found")

        await db.execute(
            bookmark_tags.delete().where(
                bookmark_tags.c.bookmark_id == bookmark.id,
                bookmark_tags.c.tag_id == tag_id,
            )
        )
        await db.commit()

        logger.info(f"Removed tag from bookmark")
        return True

    async def get_bookmark_tags(
        self, db: AsyncSession, user_id: UUID, bookmark_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tags for a bookmark.

        Args:
            db: SQLAlchemy session
            user_id: The user's ID
            bookmark_id: The bookmark's ID

        Returns:
            List of tag objects
        """
        logger.info(f"Getting tags for bookmark {bookmark_id}")

        result = await db.execute(
            sa.select(BookmarkModel).where(
                BookmarkModel.id == UUID(bookmark_id),
                BookmarkModel.user_id == user_id,
            )
        )
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            return []

        result = await db.execute(
            sa.select(TagModel)
            .join(bookmark_tags, TagModel.id == bookmark_tags.c.tag_id)
            .where(bookmark_tags.c.bookmark_id == bookmark.id)
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
