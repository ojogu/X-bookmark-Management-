from typing import Any, Dict
from uuid import UUID
from .utils import _clean_structure, read_json_file

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from src.v1.service.user import UserService
from datetime import datetime, timedelta, timezone 
from src.v1.schemas.bookmark import BookmarkResponse
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
        
    
    @staticmethod
    def parse_bookmarks_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse bookmark data into a clean structure:
        Each bookmark contains internal_id, post, and author.
        Global meta is stored separately at the top level.
        Missing/None values are replaced with safe defaults.
        """
        logger.info("Starting to parse bookmark data.")
        parsed = {"bookmarks": [], "meta": {}}

        # Extract global meta
        parsed["meta"] = data.get("meta", {})
        logger.debug(f"Extracted global meta: {parsed['meta']}")

        # Process bookmarks safely
        for bookmark in data.get("bookmarks", []):
            if not bookmark:
                logger.debug("Skipping empty bookmark entry.")
                continue  # skip empty dicts

            internal_id = bookmark.get("internal_id", "")
            if isinstance(internal_id, UUID):
                internal_id = str(internal_id)
                logger.debug(f"Converted internal_id UUID to string: {internal_id}")

            # Build author safely
            author_data = bookmark.get("author", {}) or {}
            author = {
                "id": author_data.get("id", ""),
                "username": author_data.get("username", ""),
                "name": author_data.get("name", ""),
                "profile_image_url": author_data.get("profile_image_url", ""),
            }
            logger.debug(f"Processed author data: {author}")

            # Build post safely
            post = {
                "id": bookmark.get("id", ""),
                "text": bookmark.get("text", ""),
                # "author_id": author_data.get("id", ""),
                "created_at": bookmark.get("created_at", ""),
                "metrics": bookmark.get("metrics", {}) or {},
                "lang": bookmark.get("lang", ""),
                "possibly_sensitive": bookmark.get("possibly_sensitive", False),
            }
            logger.debug(f"Processed post data: {post}")

            # Final structured bookmark
            structured_bookmark = {
                "internal_id": internal_id,
                "post": post,
                "author": author,
            }
            parsed["bookmarks"].append(structured_bookmark)
            logger.debug(f"Added structured bookmark: {structured_bookmark}")
        
        logger.info(f"Successfully parsed {len(parsed['bookmarks'])} bookmarks.")
        return parsed

    async def write_bookmark(self, bookmark_data:dict):
        """
        this is to write the bookmark to the database, parse each field to the correct table
        """
        logger.info(f"Attempting to write bookmark data to the database.")
        parsed_data = BookmarkService.parse_bookmarks
        # Placeholder for actual database write logic
        # In a real scenario, this would involve interacting with the ORM/DB
        try:
            # Example: Assuming bookmark_data needs to be saved
            # For now, just log the data
            logger.debug(f"Bookmark data received for writing: {bookmark_data}")
            # Simulate a successful write
            logger.info("Bookmark data successfully processed for writing (simulated).")
            return {"status": "success", "message": "Bookmark data processed for writing."}
        except Exception as e:
            logger.error(f"Error writing bookmark data: {e}", exc_info=True)
            raise ServerError(f"Failed to write bookmark: {e}")
        
    async def fetch_store_bookmark(self,access_token, user_id, x_id, max_results):
        logger.info(f"Attempting to fetch and store bookmarks for user with id: {user_id}")
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            logger.warning(f"User with id: {user_id} not found during bookmark fetch attempt.")
            raise NotFoundError("User not found")
        logger.debug(f"User {user_id} found. Proceeding to fetch bookmarks.")
        
        #fetching from db, since we have a cron job that fetches from the api and updates db
        try:
            bookmark_data = read_json_file("src/v1/service/bookmark.json")  # returns list of dicts
            logger.debug(f"Read bookmark data from file: {len(bookmark_data)} entries.")
            clean_data = _clean_structure(bookmark_data)
            logger.debug("Cleaned bookmark data structure.")
            validated_data = BookmarkResponse(**clean_data).model_dump()
            logger.info(f"Successfully fetched and validated bookmark data for user: {user_id}.")
            return validated_data
        except FileNotFoundError:
            logger.error("Bookmark data file not found.", exc_info=True)
            raise ServerError("Bookmark data file not found.")
        except Exception as e:
            logger.error(f"Error fetching or structuring bookmark data for user {user_id}: {e}", exc_info=True)
            raise ServerError(f"Failed to fetch or structure bookmark data: {e}")
    
    @staticmethod 
    def parse_bookmarks(response: dict, user_id: str):
        logger.info(f"Starting to parse bookmarks for user_id: {user_id}")
        tweets_data = response.get('data', [])
        authors = {u['id']: u for u in response.get('includes', {}).get('users', [])}
        logger.debug(f"Found {len(tweets_data)} tweets and {len(authors)} authors in the response.")

        bookmarks = []
        for tweet in tweets_data:
            author = authors.get(tweet['author_id'])
            if not author:
                logger.warning(f"Author not found for tweet ID: {tweet.get('id')}, author_id: {tweet.get('author_id')}")
            
            bookmark_entry = {
                "internal_id": user_id,
                "id": tweet['id'],
                "text": tweet['text'],
                "author": {
                    "id": author['id'],
                    "username": author['username'],
                    "name": author['name'],
                    "profile_image_url": author['profile_image_url']
                } if author else None,
                "created_at": tweet.get('created_at'),
                "metrics": tweet.get('public_metrics', {}),
                "lang": tweet.get('lang'),
                "possibly_sensitive": tweet.get('possibly_sensitive', False),
            }
            bookmarks.append(bookmark_entry)
            logger.debug(f"Processed bookmark for tweet ID: {tweet['id']}")
        
        logger.info(f"Successfully parsed {len(bookmarks)} bookmarks for user_id: {user_id}")
        
        data = {
            "bookmarks": bookmarks,
            "meta": response.get("meta", {})
        }
        logger.debug(f"Combined bookmarks and meta data. Meta: {data['meta']}")
        cleaned_data = _clean_structure(data)
        logger.debug("Cleaned the structured bookmark data.")
        validated_data = BookmarkResponse(**cleaned_data)
        logger.info(f"Final parsed and validated bookmark for user: {user_id}.")
        return validated_data
    
        # bookmarks = await twitter_service.get_bookmarks(                                                    access_token=access_token, 
        #     user_id = user_id,
        #     x_id = x_id,
        #     max_results = max_results)
        # return bookmarks
