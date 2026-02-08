import json
import re
from typing import Union
from src.utils.log import setup_logger
from src.v1.service.user import UserService
from src.v1.auth.service import encrypt_token, decrypt_token
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.auth.twitter_auth import TwitterAuthService


logger = setup_logger(__name__, file_path="auth.log")



async def get_valid_tokens(user_id: str, db: AsyncSession) -> dict:
    """
    Get valid tokens for a user, refreshing if expired.
    
    This function now uses the new dependency injection approach to avoid
    circular dependencies between UserService and TwitterAuthService.
    
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
        # Create services with dependency injection
        user_service: UserService = UserService(db=db)
        twitter_auth_service = TwitterAuthService(user_service)
        
        # Use the new UserService method that accepts the refresh service
        tokens = await user_service.get_valid_tokens(user_id=user_id, refresh_service=twitter_auth_service)
        logger.info(f"Successfully retrieved valid tokens for user: {user_id}")
        return tokens
            
    except Exception as e:
        logger.error(f"An error occurred while getting valid tokens for user {user_id}: {e}", exc_info=True)
        raise


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
