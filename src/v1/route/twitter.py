from fastapi import APIRouter, Request, Depends
from src.v1.auth.service import AccessTokenBearer, auth_service
from src.utils.log import setup_logger
from src.v1.service.utils import get_valid_tokens
from src.v1.service.twitter import twitter_service
access_token_bearer = AccessTokenBearer()
logger = setup_logger(__name__, file_path="auth.log")

twitter_router = APIRouter(prefix="/twitter")

@twitter_router.get("/user-info")
async def get_user_info(user_details:AccessTokenBearer = Depends(access_token_bearer)):
    user_id = user_details["user"]["user_id"]
    access_token = await get_valid_tokens(user_id)
    user_info = await twitter_service.get_user_info(access_token)
    return user_info

@twitter_router.get("/bookmarks")
async def get_user_info(user_details:AccessTokenBearer = Depends(access_token_bearer)):
    user_id = user_details["user"]["user_id"]
    access_token = await get_valid_tokens(user_id)
    user_bookmarks = await twitter_service.get_bookmarks(access_token)
    return user_bookmarks
