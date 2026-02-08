import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from datetime import datetime, timedelta, timezone 
from .interfaces import TokenRefreshService
from src.v1.auth.service import encrypt_token, decrypt_token
# from src.v1.auth.service import au
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
    BaseExceptionClass
    
)

from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="user.log")



def parse_token_data(token_dict: dict) -> dict:
    """
    Normalize token expiry so that token_dict always has `expires_at` (datetime in UTC).
    Handles both 'expires_in' (int seconds) and 'expires_at' (timestamp or datetime).
    Also encrypts access_token and refresh_token if present.
    """
    updated_dict = token_dict.copy()

    if "expires_at" in updated_dict:
        expires_at_val = updated_dict["expires_at"]
        if isinstance(expires_at_val, datetime):
            # Already a datetime
            expires_at = expires_at_val
        else:
            try:
                # Try parsing string to datetime (if provider sends ISO format)
                expires_at = datetime.fromisoformat(str(expires_at_val))
            except ValueError:
                raise ValueError(f"Unrecognized expires_at format: {expires_at_val}")
    elif "expires_in" in updated_dict:
        try:
            expires_in_seconds = int(updated_dict["expires_in"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert 'expires_in' to integer: {updated_dict['expires_in']}") from e
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        del updated_dict["expires_in"]
    else:
        raise KeyError("No 'expires_in' or 'expires_at' key found in token dictionary")

    updated_dict["expires_at"] = expires_at

    # Encrypt access_token and refresh_token if present
    if "access_token" in updated_dict:
        updated_dict["access_token"] = encrypt_token(updated_dict["access_token"])
    if "refresh_token" in updated_dict:
        updated_dict["refresh_token"] = encrypt_token(updated_dict["refresh_token"])

    return updated_dict


class UserService():
    def __init__(self, db:AsyncSession):
        self.db = db

    async def create_user(self, user_data: dict):
        x_id = user_data["x_id"]
        logger.info(f"Attempting to create user with x_id: {x_id}")
        
        user = await self.check_if_user_exist_X_id(x_id)
        if user:
            logger.warning(f" {x_id} already exists. Return our jwt to authenticate user for our app")
            return user
        
            
        new_user = User(**user_data)
        self.db.add(new_user)
        logger.debug(f"Adding new user to database session: {user_data}")
        
        try:
            await self.db.flush()  # Use flush to get potential errors before commit
            await self.db.refresh(new_user) # Refresh to get DB defaults like ID, created_at
            # await self.db.commit() 
            logger.info(f"Successfully created new user with x_id: {x_id}")
            return new_user
        

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"SQLAlchemy error while creating user {x_id}: {str(e)}")
            raise ServerError() 


    async def store_user_token(self, user_id: str, user_token: dict):
        logger.info(f"user tokens: {user_token}")
        updated_user_tokens = parse_token_data(user_token)
        logger.info(f"updated user tokens: {updated_user_tokens}")
        user = await self.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError("User id not found")

        result = await self.db.execute(
            sa.select(UserToken).where(UserToken.user_id == user_id)
        )
        existing_token = result.scalar_one_or_none()
        logger.info(f"existing tokens: {existing_token}")
        if existing_token:
            logger.info(f"Found existing token for user {user_id}")
            for key, value in updated_user_tokens.items():
                setattr(existing_token, key, value)
            user_tokens = existing_token
        else:
            logger.info(f"No existing token for user {user_id}, creating new one.")
            user_tokens = UserToken(user_id=user_id, **updated_user_tokens)

        try:
            self.db.add(user_tokens)
            # await self.db.flush()
            await self.db.commit()
            await self.db.refresh(user_tokens)
            logger.info(f"Successfully stored token for user_id: {user_tokens.user_id}")
            return user_tokens
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error while storing token for user {user_id}: {e}")
            raise ServerError(f"Could not store token: {e}") from e

    
    
    async def check_if_user_exist_X_id(self, x_id: str):
        result = await self.db.execute(sa.select(User).where(x_id == User.x_id))
        if not result:
            return None
        return result.scalar_one_or_none() 

    
    async def check_if_user_exists_user_id(self, user_id:str):
        result = await self.db.execute(sa.select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    
    async def fetch_user_token(self, user_id):
        result = await self.db.execute(
            sa.select(UserToken).where(UserToken.user_id == user_id)
        )
        user_token = result.scalar_one_or_none()

        if user_token:
            # Decrypt the encrypted tokens
            decrypted_access_token = decrypt_token(user_token.access_token)
            decrypted_refresh_token = decrypt_token(user_token.refresh_token)

            # Return token data as a dictionary with decrypted tokens
            return {
                "user_id": user_token.user_id,
                "access_token": decrypted_access_token,
                "token_type": user_token.token_type,
                "scope": user_token.scope,
                "refresh_token": decrypted_refresh_token,
                "expires_at": user_token.expires_at,
                "is_expired": user_token.is_expired
            }
        return None
    

    
    async def is_token_expired(self, user_id):
        logger.info(f"Checking if token is expired for user_id: {user_id}")
        try:
            result = await self.db.execute(
                sa.select(UserToken).where(
                    sa.and_(
                        UserToken.user_id == user_id,
                        UserToken.is_expired 
                    )
                )
            )
            token_is_expired = result.scalar_one_or_none() is not None
            if token_is_expired:
                logger.info(f"Token for user_id: {user_id} has expired.")
            else:
                logger.info(f"Token for user_id: {user_id} has not expired.")
            return token_is_expired
        except SQLAlchemyError as e:
            logger.error(f"Database error while checking token expiration for user {user_id}: {e}", exc_info=True)
            raise ServerError(f"Could not check token expiration: {e}") from e


    async def fetch_all_users_id(self):
        stmt = await self.db.execute(
            sa.select(
                User.id
            )
        )
        return stmt.scalars().all() #scalars return multiple rows, but only the first column/object from each row.
    
    # async def fetch_X_id_for_a_user(self, user_id:str):
    #     # user_id = await self.check_if_user_exists_user_id(user_id)
    #     stmt = (
    #         sa.select(User.x_id)
    #         .join(UserToken, User.id == UserToken.user_id)
    #         .where(User.id == user_id)   # use the checked user_id here
    #     )
    #     result = await self.db.execute(stmt)
    #     return result.scalar_one_or_none()
    
    async def fetch_X_id_for_a_user(self, user_id: str):
        user = await self.check_if_user_exists_user_id(user_id)
        return user.x_id

    async def get_valid_tokens(self, user_id: str, refresh_service: TokenRefreshService) -> dict:
        """
        Get valid tokens for a user, refreshing if expired.
        
        This method uses dependency injection to avoid circular dependencies
        between UserService and TwitterAuthService.
        
        Args:
            user_id: The user ID to fetch tokens for
            refresh_service: TokenRefreshService implementation for refreshing tokens
            
        Returns:
            Dictionary containing access_token, user_id, and x_id
            
        Raises:
            ValueError: If no tokens found for user
            Exception: For other errors during token processing
        """
        logger.info(f"Attempting to get valid tokens for user: {user_id}")
        try:
            x_id = await self.fetch_X_id_for_a_user(user_id)
            
            tokens = await self.fetch_user_token(user_id=user_id)
            if not tokens:
                logger.warning(f"No tokens found for user: {user_id}")
                raise ValueError(f"No tokens found for user: {user_id}")
            
            current_time = datetime.now(timezone.utc)
            is_expired = current_time > tokens["expires_at"] if tokens["expires_at"] else True
            
            # Check expiration directly on the fetched token
            if is_expired:
                logger.info(f"Token expired for user: {user_id}, fetching new tokens")
                new_tokens = await refresh_service.refresh_token(tokens["refresh_token"])
                logger.info(f"New token fetched for user: {user_id}")
                user_tokens = await self.store_user_token(user_id=user_id, user_token=new_tokens)
                logger.info(f"New token stored for user: {user_id}")
            else:
                logger.info(f"Token for user: {user_id} is still valid")
                user_tokens = tokens

            return {
                "access_token": user_tokens["access_token"],
                "user_id": user_tokens["user_id"],
                "x_id": x_id
            }
            
        except Exception as e:
            logger.error(f"An error occurred while getting valid tokens for user {user_id}: {e}", exc_info=True)
            raise
    
    
    