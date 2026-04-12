#Direct in-app endpoint to fetch fresh data directly from X
from fastapi import APIRouter, Request, Depends
from src.v1.auth.service import AccessTokenBearer, auth_service
from src.utils.log import get_logger
from src.v1.model.users import User
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
from src.v1.route.dependencies import get_user_service
from src.v1.service.user import UserService
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.config import config
from urllib.parse import urlencode
from src.v1.route.dependencies import (
    get_user_service,
    get_bookmark_service,
    get_current_user,
)
from src.v1.service.bookmark import BookmarkService
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
from src.v1.schemas.user import UserInfoFromX

access_token_bearer = AccessTokenBearer()
logger = get_logger(__name__)

twitter_router = APIRouter(prefix="/X")


@twitter_router.get("/user-info/fresh", response_model=UserInfoFromX)
async def get_user_info_fresh(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        user_id = current_user.id
        tokens = await get_valid_tokens(user_id, db)
        access_token = tokens.get("access_token")
        user_info = await twitter_service.get_user_info(access_token)

        user_service = UserService(db=db)
        await user_service.update_user_info(user_id, user_info)

        return user_info
    except Exception as e:
        logger.error(f"Error getting fresh user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@twitter_router.get("/bookmarks")
async def get_bookmarks(
    pagination_token: Optional[str] = None,
    max_results: int = 2,  # query parameter
    current_user: User = Depends(get_current_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
    db: AsyncSession = Depends(get_session),
):

    try:
        user_id = current_user.id
        x_id = current_user.x_id
        # TODO: fetch from db, not direct api
        tokens = await get_valid_tokens(user_id, db)
        access_token = tokens.get("access_token")
        bookmarks = await twitter_service.get_bookmarks(
            access_token=access_token,
            user_id=user_id,
            x_id=x_id,
            max_results=max_results,
            pagination_token=pagination_token,
        )
        return bookmarks
    except NotFoundError as e:
        logger.error(e)
    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
