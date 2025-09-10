import json
import re
from typing import Union
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from src.v1.service.user import UserService
from datetime import datetime, timedelta, timezone 
from src.v1.schemas.bookmark import ListBookmarkSchema
from src.v1.service.twitter import twitter_service
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


def _clean_value(value):
    """Clean strings by removing newlines/tabs and extra spaces."""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value

def _clean_structure(data):
    """Recursively clean dicts/lists of strings."""
    if isinstance(data, dict):
        return {k: _clean_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_clean_structure(item) for item in data]
    else:
        return _clean_value(data)

def read_json_file(path: str) -> Union[dict, list]:
    """
    Read a JSON file and return its content as a cleaned Python dictionary or list.
    All strings will be stripped of newlines, tabs, and excessive spaces.
    """
    with open(path, "r", encoding="utf-8") as file:
        raw_data = json.load(file)
        return _clean_structure(raw_data)




class BookmarkService():
    def __init__(self,  user_service: UserService):
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
        
        # bookmarks = await twitter_service.get_bookmarks(                                                    access_token=access_token, 
        #     user_id = user_id,
        #     x_id = x_id,
        #     max_results = max_results)
        # return bookmarks
