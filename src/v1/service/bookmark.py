from typing import Any, Dict
from uuid import UUID
from .utils import _clean_structure, read_json_file

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from src.v1.service.user import UserService
from datetime import datetime, timedelta, timezone 
from src.v1.schemas.bookmark import BookmarkResponse, Author, Meta, Metrics, Post, Bookmark
from src.v1.model import Author as AuthorModel, Post as PostModel, Bookmark as BookmarkModel
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
    BaseExceptionClass
    
)


from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="bookmark.log")




class BookmarkService():
    def __init__(self,  user_service: UserService=None):
        self.user_service = user_service
    
    
    async def check_if_author_exists(self, db:AsyncSession, author_id):
        result = await db.execute(
            sa.select(AuthorModel).where(author_id == AuthorModel.author_id_from_x)
        )
        if not result:
            return None
        return result.scalar_one_or_none()
    
    
    async def check_if_post_exists(self, db:AsyncSession, post_id):
        result = await db.execute(
            sa.select(PostModel).where(post_id == PostModel.post_id)
        )
        if not result:
            return None
        return result.scalar_one_or_none()
    
    async def check_if_bookmark_exists(self, db:AsyncSession, post_id, user_id):
        result = await db.execute(
            sa.select(BookmarkModel).where(
                post_id == PostModel.id,
                user_id == User.id
                
                )
        )
        if not result:
            return None
        return result.scalar_one_or_none()
    
    
    async def fetch_next_token(self, db:AsyncSession, user_id):
        next_token = await db.execute(
            sa.select(BookmarkModel.next_token).where(
                user_id == BookmarkModel.user_id
            )
        )
        if not next_token:
            return None
        return next_token.scalar_one_or_none()
    
    async def save_bookmarks(self, db: AsyncSession, user_id: str, api_response: Dict[str, Any]):
        """
        Full pipeline to parse Twitter bookmarks API response and save to DB.

        Args:
            db: SQLAlchemy db object
            user_id: ID of the user whose bookmarks these are
            api_response: Raw JSON response from Twitter API
        """
        logger.info(f"Starting bookmark save pipeline for user_id={user_id}")
        
        #check if user exists
        logger.debug(f"Checking if user {user_id} exists")
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            raise NotFoundError(f"user: {user_id} does not exists" )
        
        # Parse & validate API response using Pydantic
        logger.debug(f"Parsing API response for user {user_id}")
        validated_response = BookmarkService.parse_bookmarks_response(api_response, user_id)
        logger.info(f"Found {len(validated_response.bookmarks)} bookmarks to process for user {user_id}")
        
        logger.info(f"parsed data: {validated_response}")
        # Iterate through bookmarks and upsert data
        for index, bm in enumerate(validated_response.bookmarks, 1):
            logger.debug(f"Processing bookmark {index}/{len(validated_response.bookmarks)}")
            post_data = bm.post.model_dump() if hasattr(bm, 'post') else bm.model_dump().get('post')
            author_data = bm.author.model_dump() if hasattr(bm, 'author') else bm.model_dump().get('author')

            # ---- Handle Author ----
            logger.debug(f"Checking author {author_data['id']}")
            author = await self.check_if_author_exists(db,author_data['id'])
            if not author:
                logger.debug(f"Creating new author record for {author_data['id']}")
                author = AuthorModel(
                    username=author_data.get('username', ''),
                    name=author_data.get('name', ''),
                    profile_image_url = str(author_data.get('profile_image_url', '')),
                    author_id_from_x=author_data.get('id', '')
                )
                db.add(author)
                await db.flush()

            # ---- Handle Post ----
            logger.debug(f"Checking post {post_data['id']}")
            post = await self.check_if_post_exists(db,post_data['id'])
            if not post:
                logger.debug(f"Creating new post record for {post_data['id']}")
                post = PostModel(
                    post_id=post_data.get('id', ''),
                    text=post_data.get('text', ''),
                    created_at_from_twitter=post_data.get('created_at'),
                    lang=post_data.get('lang', ''),
                    possibly_sensitive=post_data.get('possibly_sensitive', False),
                    author_id=author.id
                )
                db.add(post)
                await db.flush()

            # ---- Handle Bookmark ----
            logger.debug(f"Checking if bookmark exists for post {post.id} and user {user_id}")
            existing_bm = await self.check_if_bookmark_exists(db, post_id=post.id, user_id=user_id)
    
            if not existing_bm:
                logger.debug(f"Creating new bookmark for post {post.id}")
                bookmark = BookmarkModel(
                    user_id=user_id,
                    post_id=post.id,
                    next_token=validated_response.meta.next_token
                )
                db.add(bookmark)

        # Commit all changes
        try:
            await db.commit()
            logger.info(f"Successfully saved all {len(validated_response.bookmarks)} bookmarks for user_id={user_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save bookmarks for user_id={user_id}: {str(e)}", exc_info=True)
            raise

      
    @staticmethod  
    def parse_bookmarks_response(response: Dict[str, Any], user_id: str) -> BookmarkResponse:
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
        
    
        authors_map = {u["id"]: u for u in response.get("includes", {}).get("users", []) or []}
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
                profile_image_url=author_data.get("profile_image_url", None)
            )

            metrics_data = tweet.get("public_metrics", {}) or {}
            metrics = Metrics(
                retweet_count=metrics_data.get("retweet_count", 0),
                reply_count=metrics_data.get("reply_count", 0),
                like_count=metrics_data.get("like_count", 0),
                quote_count=metrics_data.get("quote_count", 0),
                bookmark_count=metrics_data.get("bookmark_count", 0),
                impression_count=metrics_data.get("impression_count", 0)
            )

            post = Post(
                id=tweet.get("id", ""),
                text=tweet.get("text", ""),
                author_id=tweet.get("author_id", ""),
                created_at=tweet.get("created_at"),
                metrics=metrics,
                lang=tweet.get("lang", ""),
                possibly_sensitive=tweet.get("possibly_sensitive", False)
            )

            bookmark = Bookmark(
                internal_id=str(user_id),
                post=post,
                author=author
            )

            bookmarks_list.append(bookmark)

        structured_data = {
            "bookmarks": bookmarks_list,
            "meta": Meta(
                result_count=meta.get("result_count", len(bookmarks_list)),
                next_token=meta.get("next_token")
            )
        }

        cleaned_data = _clean_structure(structured_data)

        validated_response = BookmarkResponse(**cleaned_data)

        logger.info(f"Parsed {len(validated_response.bookmarks)} bookmarks for user_id={user_id}")
        return validated_response



