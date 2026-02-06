from datetime import datetime, timezone
import json
import re
from typing import Union
from src.utils.log import setup_logger
from src.v1.service.user import UserService
# from src.utils.db import get_manual_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.auth.twitter_auth import TwitterAuthService

logger = setup_logger(__name__, file_path="auth.log")

async def get_valid_tokens(user_id: str, db: AsyncSession) -> dict:
    """
    Get valid tokens for a user, refreshing if expired.

    Args:
        user_id: The user ID to fetch tokens for
        db: Async database session

    Returns:
        Dictionary containing access_token, user_id, and x_id

    Raises:
        ValueError: If no tokens found for user
        Exception: For other errors during token processing
    """
    logger.info(f"Attempting to get valid tokens for user: {user_id}")
    try:
        #TODO: use depedency injection rather than manual instansiation
        user_service: UserService = UserService(db=db)
        twitter_auth_service = TwitterAuthService(user_service)
        x_id = await user_service.fetch_X_id_for_a_user(user_id)
        
        tokens = await user_service.fetch_user_token(user_id=user_id)
        if not tokens:
            logger.warning(f"No tokens found for user: {user_id}")
            raise ValueError(f"No tokens found for user: {user_id}")
        
        current_time = datetime.now(timezone.utc)
        is_expired = current_time > tokens["expires_at"] if tokens["expires_at"] else True
        
    
        # Check expiration directly on the fetched token
        if is_expired:
            logger.info(f"Token expired for user: {user_id}, fetching new tokens")
            new_tokens = await twitter_auth_service.refresh_token(tokens["refresh_token"])
            logger.info(f"New token fetched for user: {user_id}")
            user_tokens = await user_service.store_user_token(user_id=user_id, user_token=new_tokens)
            logger.info(f"New token stored for user: {user_id}")
        else:
            logger.info(f"Token for user: {user_id} is still valid")
            user_tokens = tokens

        return _create_token_response(user_tokens, x_id)
            
    except Exception as e:
        logger.error(f"An error occurred while getting valid tokens for user {user_id}: {e}", exc_info=True)
        raise

def _create_token_response(user_tokens: dict, x_id: str) -> dict:
    """Create a standardized token response dictionary."""
    return {
        "access_token": user_tokens["access_token"],
        "user_id": user_tokens["user_id"],
        "x_id": x_id
    }

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


# async def fetch_all_user_id_token():
#     db = await get_manual_db_session()
