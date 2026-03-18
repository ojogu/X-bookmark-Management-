from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.v1.auth.service import AccessTokenBearer
from src.v1.service.user import UserService
from src.v1.service.bookmark import BookmarkService
from src.v1.auth.twitter_auth import TwitterAuthService


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
    return BookmarkService(user_service=user_service)


def get_twitter_client(user_service: UserService = Depends(get_user_service)):
    """
    Dependency function to get an instance of TwitterAuthService.

    Args:
        user_service (UserService): The user service dependency.

    Returns:
        TwitterAuthService: An instance of the Twitter service.
    """
    return TwitterAuthService(user_service)

async def get_current_user(user_details:dict = Depends(AccessTokenBearer()),
user_service: UserService = Depends(get_user_service)
):
    user_id = user_details["user"]["user_id"]
    user = await user_service.check_if_user_exists_user_id(user_id)
    return user