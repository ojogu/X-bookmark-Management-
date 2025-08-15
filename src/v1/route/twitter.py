from fastapi import APIRouter, Request, Depends
from src.v1.auth.service import AccessTokenBearer, auth_service
from src.utils.log import setup_logger
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
from src.v1.schemas.bookmark import BookmarkSchema
from typing import List
from fastapi import APIRouter, HTTPException, status, Request, Depends
from src.v1.service.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.config import config
from urllib.parse import urlencode
from src.v1.service.bookmark import BookmarkService

access_token_bearer = AccessTokenBearer()
logger = setup_logger(__name__, file_path="auth.log")

twitter_router = APIRouter(prefix="/twitter")


def get_user_service(db: AsyncSession = Depends(get_session)):
    """
    Dependency function to get an instance of UserService.

    Returns:
        UserService: An instance of the user service.
    """
    return UserService(db=db)



def get_bookmark_service(user_service: UserService = Depends(get_user_service)):
    """
    Dependency function to get an instance of BookmarkService.

    Args:
        user_service (UserService): The user service dependency.

    Returns:
        BookmarkService: An instance of the BookmarkService service.
    """
    return BookmarkService(user_service)


@twitter_router.get("/user-info")
async def get_user_info(
    user_details:AccessTokenBearer = Depends(access_token_bearer)
    ):
    # logger.info(f"user details: {user_details}")
    user_id = user_details["user"]["user_id"]
    access_token = await get_valid_tokens(user_id)
    user_info = await twitter_service.get_user_info(access_token)
    return user_info


@twitter_router.get("/bookmarks")
async def get_bookmarks(
    user_details: AccessTokenBearer = Depends(access_token_bearer), max_results: int = 10, bookmark_service:BookmarkService = Depends(get_bookmark_service)
    ):
    
    user_id = user_details["user"]["user_id"]
    x_id = user_details["user"]["x_id"]
    access_token = await get_valid_tokens(user_id)
    bookmarks = await bookmark_service.create_bookmark(
        max_results,
        access_token=access_token, 
        user_id = user_id,
        x_id = x_id,
        )
    return bookmarks
