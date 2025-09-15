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
                post_id == PostModel.post_id,
                user_id == User.id
                
                )
        )
        if not result:
            return None
        return result.scalar_one_or_none()
    
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
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError(f"user: {user_id} does not exists" )
        
        # Parse & validate API response using Pydantic
        validated_response = BookmarkService.parse_bookmarks_response(api_response, user_id)

        # Iterate through bookmarks and upsert data
        for bm in validated_response.bookmarks:
            post_data = bm.post.model_dump() if hasattr(bm, 'post') else bm.model_dump().get('post')
            author_data = bm.author.model_dump() if hasattr(bm, 'author') else bm.model_dump().get('author')

            # ---- Handle Author ----
            author = await self.check_if_author_exists(db,author_data['id'])
            if not author:
                author = AuthorModel(
                    username=author_data.get('username', ''),
                    name=author_data.get('name', ''),
                    profile_image_url=author_data.get('profile_image_url', ''),
                    author_id_from_x=author_data.get('id', '')
                )
                await db.add(author)
                await db.flush()  # flush to get author.id for FK

            # ---- Handle Post ----
            post = await self.check_if_post_exists(db,post_data['id'])
            if not post:
                post = PostModel(
                    post_id=post_data.get('id', ''),
                    text=post_data.get('text', ''),
                    created_at_from_twitter=post_data.get('created_at'),
                    lang=post_data.get('lang', ''),
                    possibly_sensitive=post_data.get('possibly_sensitive', False),
                    author_id=author.id
                )
                await db.add(post)
                await db.flush()  # flush to get post.id for FK

            # ---- Handle Bookmark ----
            existing_bm = await self.check_if_bookmark_exists(db, post_id=post.id, user_id=user_id)
    
            if not existing_bm:
                bookmark = BookmarkModel(
                    user_id=user_id,
                    post_id=post.id,
                    next_token=validated_response.meta.next_token
                )
                await db.add(bookmark)

        # 3️⃣ Commit all changes
        try:
            await db.commit()
            logger.info(f"Successfully saved bookmarks for user_id={user_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save bookmarks for user_id={user_id}: {e}")
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
        logger.info(f"Parsing bookmarks for user_id={user_id}")

        tweets_data = response.get("data", []) or []
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



    # async def write_bookmark(self, bookmark_data:dict):
    #     """
    #     this is to write the bookmark to the database, parse each field to the correct table
    #     """
    #     logger.info(f"Attempting to write bookmark data to the database.")
    #     parsed_data = BookmarkService.parse_bookmarks
    #     # Placeholder for actual database write logic
    #     # In a real scenario, this would involve interacting with the ORM/DB
    #     try:
    #         # Example: Assuming bookmark_data needs to be saved
    #         # For now, just log the data
    #         logger.debug(f"Bookmark data received for writing: {bookmark_data}")
    #         # Simulate a successful write
    #         logger.info("Bookmark data successfully processed for writing (simulated).")
    #         return {"status": "success", "message": "Bookmark data processed for writing."}
    #     except Exception as e:
    #         logger.error(f"Error writing bookmark data: {e}", exc_info=True)
    #         raise ServerError(f"Failed to write bookmark: {e}")
        
    # async def fetch_store_bookmark(self,access_token, user_id, x_id, max_results):
    #     logger.info(f"Attempting to fetch and store bookmarks for user with id: {user_id}")
    #     user = await self.user_service.check_if_user_exists_user_id(user_id)
    #     if not user:
    #         logger.warning(f"User with id: {user_id} not found during bookmark fetch attempt.")
    #         raise NotFoundError("User not found")
    #     logger.debug(f"User {user_id} found. Proceeding to fetch bookmarks.")
        
    #     #fetching from db, since we have a cron job that fetches from the api and updates db
    #     try:
    #         bookmark_data = read_json_file("src/v1/service/bookmark.json")  # returns list of dicts
    #         logger.debug(f"Read bookmark data from file: {len(bookmark_data)} entries.")
    #         clean_data = _clean_structure(bookmark_data)
    #         logger.debug("Cleaned bookmark data structure.")
    #         validated_data = BookmarkResponse(**clean_data).model_dump()
    #         logger.info(f"Successfully fetched and validated bookmark data for user: {user_id}.")
    #         return validated_data
    #     except FileNotFoundError:
    #         logger.error("Bookmark data file not found.", exc_info=True)
    #         raise ServerError("Bookmark data file not found.")
    #     except Exception as e:
    #         logger.error(f"Error fetching or structuring bookmark data for user {user_id}: {e}", exc_info=True)
    #         raise ServerError(f"Failed to fetch or structure bookmark data: {e}")
    
    
        # bookmarks = await twitter_service.get_bookmarks(                                                    access_token=access_token, 
        #     user_id = user_id,
        #     x_id = x_id,
        #     max_results = max_results)
        # return bookmarks
