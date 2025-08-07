from src.utils.log import setup_logger
from src.v1.service.user import UserService
from src.utils.db import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.auth.twitter_auth import TwitterAuthService

logger = setup_logger(__name__, file_path="auth.log")

user_service: UserService = UserService(db = get_session)

twitter_service  = TwitterAuthService(user_service)
async def get_valid_tokens(user_id):
    tokens = await user_service.fetch_user_token(user_id=user_id)
    is_expired = await user_service.is_token_expired(user_id=user_id)
    if is_expired:
        logger.info("token expired, fetching new tokens")
        new_tokens = await twitter_service.refresh_token(tokens.refresh_token)
        user_tokens = await user_service.store_user_token(user_id=user_id, user_token=new_tokens)
        return user_tokens.access_token
        
        #fetch new tokens with refresh token, upsert it, return access token
        
    else:
        return tokens.access_token
        


