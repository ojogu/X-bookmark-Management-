import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from src.v1.service.user import UserService
from datetime import datetime, timedelta, timezone 
from src.v1.schemas.bookmark import BookmarkSchema
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

def read_json_file(path: str) -> str:
    """
    Read a JSON file and return its raw JSON string.
    """
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


class BookmarkService():
    def __init__(self, db:AsyncSession, user_service: UserService):
        self.db = db
        self.user_service = user_service
        
        
    async def create_bookmark(self, access_token, user_id, max_results):
        logger.info(f"attempting for creating bookmarks for user with id: {user_id}")
        user = self.user_service.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        # bookmarks = await twitter_service.get_bookmarks(access_token, user_id, max_results)
        bookmark_data = read_json_file("bookmark.json")
        validated_data = BookmarkSchema(**bookmark_data).model_dump()
        return validated_data
        

    
