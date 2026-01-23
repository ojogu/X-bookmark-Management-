import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
from datetime import datetime, timedelta, timezone 
from src.v1.auth.service import auth_service
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
    cipher = auth_service.encryption_key()
    if "access_token" in updated_dict:
        updated_dict["access_token"] = cipher.encrypt(updated_dict["access_token"].encode()).decode()
    if "refresh_token" in updated_dict:
        updated_dict["refresh_token"] = cipher.encrypt(updated_dict["refresh_token"].encode()).decode()

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
        updated_user_tokens = parse_token_data(user_token)
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

        try:
            self.db.add(user_tokens)
            await self.db.flush()
            # await self.db.refresh(user_tokens)
            await self.db.commit()
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
        return result.scalar_one_or_none()
    
    # async def fetch_user_id(self, user_id):
    #     result = await self.db.execute(
    #         sa.select(User.id).
    #         where(
    #             User.id == user_id
    #         )
    #     )
    #     return result.scalar_one_or_none()
    
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