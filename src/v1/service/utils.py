from datetime import datetime, timezone
from src.utils.log import setup_logger
from src.v1.service.user import UserService
from src.utils.db import get_manual_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.auth.twitter_auth import TwitterAuthService

logger = setup_logger(__name__, file_path="auth.log")

async def get_valid_tokens(user_id):
    logger.info(f"Attempting to get valid tokens for user: {user_id}")
    try:
        db = await get_manual_db_session()
        user_service: UserService = UserService(db=db)
        twitter_service = TwitterAuthService(user_service)
        
        tokens = await user_service.fetch_user_token(user_id=user_id)
        if not tokens:
            logger.warning(f"No tokens found for user: {user_id}")
            return None
        
        current_time = datetime.now(timezone.utc)
        is_expired = current_time > tokens.expires_at if tokens.expires_at else True
    
        # Check expiration directly on the fetched token
        if is_expired:
            logger.info(f"Token expired for user: {user_id}, fetching new tokens")
            new_tokens = await twitter_service.refresh_token(tokens.refresh_token)
            logger.info(f"New token fetched for user: {user_id}")
            logger.info(f"new tokens: {new_tokens}")
            user_tokens = await user_service.store_user_token(user_id=user_id, user_token=new_tokens)
            logger.info(f"New token stored for user: {user_id}")
            return user_tokens.access_token
        else:
            logger.info(f"Token for user: {user_id} is still valid")
            return tokens.access_token
            
    except Exception as e:
        logger.error(f"An error occurred while getting valid tokens for user {user_id}: {e}", exc_info=True)
        return None

