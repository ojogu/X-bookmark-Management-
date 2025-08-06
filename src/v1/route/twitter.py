from fastapi import APIRouter, Request, Depends
from src.v1.auth.service import AccessTokenService, auth_service
from src.utils.log import setup_logger

access_token_bearer = AccessTokenService()
logger = setup_logger(__name__, file_path="auth.log")

twitter_router = APIRouter(prefix="/twitter")

@twitter_router.get("/user-info")
async def get_user_info(security:AccessTokenService = Depends(access_token_bearer)):
    return {"msg": "auth confirmed"} 