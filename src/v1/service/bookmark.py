import json
import re
from typing import Union
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
logger = setup_logger(__name__, file_path="user.log")






class BookmarkService():
    def __init__(self,  user_service: UserService=None):
        self.user_service = user_service
        
        
    async def fetch_store_bookmark(self,access_token, user_id, x_id, max_results):
        logger.info(f"attempting for fetch bookmarks bookmarks for user with id: {user_id}")
        user = await self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        #fetching from db, since we have a cron job that fetches from the api and updates db
        bookmark_data = read_json_file("src/v1/service/bookmark.json")  # returns list of dicts
        validated_data = ListBookmarkSchema(bookmarks=bookmark_data).model_dump()
        return validated_data
    
    @staticmethod 
    def parse_bookmarks(response: dict, user_id: str):
        logger.info(f"Parsing bookmarks for user_id: {user_id}")
        tweets_data = response.get('data', [])
        authors = {u['id']: u for u in response.get('includes', {}).get('users', [])}

        bookmarks = []
        for tweet in tweets_data:
            author = authors.get(tweet['author_id'])
            bookmarks.append({
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
            })
        
        logger.info(f"Successfully parsed {len(bookmarks)} bookmarks for user_id: {user_id}")
        
        data = {
            "bookmarks": bookmarks,
            "meta": response.get("meta", {})
        }
        cleaned_data = _clean_structure(data)
        validated_data = BookmarkResponse(**cleaned_data)
        logger.info(f"final parsed bookmark for user: {user_id}: {validated_data}")
        return validated_data
    
        # bookmarks = await twitter_service.get_bookmarks(                                                    access_token=access_token, 
        #     user_id = user_id,
        #     x_id = x_id,
        #     max_results = max_results)
        # return bookmarks
