from src.utils.log import setup_logger
from src.v1.service.user import UserService
from src.utils.db import get_session
from sqlalchemy.ext.asyncio import AsyncSession


logger = setup_logger(__name__, file_path="auth.log")

user_service: UserService = UserService(db = get_session)


async def get_valid_tokens(user_id):
    tokens = await user_service.fetch_user_token(user_id=user_id)
    is_expired = await user_service.is_token_expired(user_id=user_id)
    if is_expired:
        logger.info("token expired, fetching new tokens")
        #fetch new tokens with refresh token, upsert it, return access token
        
    else:
        return tokens.access_token
        


