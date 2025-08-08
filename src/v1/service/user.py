import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from datetime import datetime, timedelta, timezone 
from src.v1.schemas.user import User_Token
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


def convert_expires_in_to_datetime(token_dict: dict) -> dict:
    """
    Convert 'expires_in' seconds to 'expires_at' datetime in a token dictionary.
    
    Args:
        token_dict (dict): Dictionary containing token data with 'expires_in' field
        
    Returns:
        dict: Updated dictionary with 'expires_at' datetime and 'expires_in' removed
        
    Raises:
        KeyError: If 'expires_in' key is not found in the dictionary
        ValueError: If 'expires_in' cannot be converted to integer
    """
    # Create a copy to avoid mutating the original dict
    updated_dict = token_dict.copy()
    
    if 'expires_in' not in updated_dict:
        raise KeyError("'expires_in' key not found in token dictionary")
    
    try:
        expires_in_seconds = int(updated_dict["expires_in"])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert 'expires_in' to integer: {updated_dict['expires_in']}") from e
    
    # Convert to datetime using the same logic as your helper method
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    
    # Inject into the dict for DB persistence
    updated_dict["expires_at"] = expires_at
    
    logger.info(f"Successfully converted {expires_in_seconds} to a datetime object {expires_at}, deleting.....")
    
    # Remove the original field as it's no longer needed
    del updated_dict["expires_in"]
    
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
            await self.db.commit()
            logger.info(f"Successfully created new user with x_id: {x_id}")
            return new_user
        
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while creating user {x_id}: {str(e)}")
            # Check if it's a unique constraint violation (though checked above, good practice)
            if "unique constraint" in str(e).lower():
                raise AlreadyExistsError(
                    f"x_id '{user_data.x_id}' is already registered (concurrent request?)."
                )
            else:
                logger.error(f"Database integrity error for user {x_id}: {str(e)}")
                raise ServerError(f"Database integrity error: {e}") from e
                
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"SQLAlchemy error while creating user {x_id}: {str(e)}")
            raise ServerError(f"Could not create user: {e}") from e


    async def store_user_token(self, user_id: str, user_token: dict):
        logger.info(f"user tokens: {user_token}")
        updated_user_tokens = convert_expires_in_to_datetime(user_token)
        logger.info(f"updated user tokens: {updated_user_tokens}")
        user = await self.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError("User id not found, register")

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
            self.db.add(user_tokens)

        try:
            await self.db.flush()
            await self.db.refresh(user_tokens)
            await self.db.commit()
            logger.info(f"Successfully stored token for user_id: {user_tokens.user_id}")
            return user_tokens
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while storing token for user {user_id}: {e}")
            if "unique constraint" in str(e).lower():
                raise AlreadyExistsError(
                    f"Token for user_id '{user_id}' already exists (concurrent request?)."
                )
            else:
                raise ServerError(f"Database integrity error: {e}") from e
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
        return result.scalar_one_or_none()
    
    async def is_token_expired(self, user_id):
        logger.info(f"Checking if token is expired for user_id: {user_id}")
        try:
            result = await self.db.execute(
                sa.select(UserToken).where(
                    sa.and_(
                        UserToken.user_id == user_id,
                        UserToken.is_expired == True
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
