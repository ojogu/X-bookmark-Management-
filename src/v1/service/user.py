import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from src.v1.model.users import User, UserToken
from sqlalchemy.exc import IntegrityError, DatabaseError, SQLAlchemyError
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

    async def store_user_token(self, user_id:str, user_token:dict):
        user = await self.check_if_user_exists_user_id(user_id)
        if not user:
            raise NotFoundError("User id not found, register")
        user_tokens = UserToken(
            user_id=user_id,
            **user_token
            )
        self.db.add(user_tokens)
        try:
            await self.db.flush() #to get potential error before commit
            await self.db.refresh(user_tokens)  # Refresh to get DB defaults like ID, created_at
            await self.db.commit()
            logger.info(f"Successfully created token for uaer with user_id: {user_tokens.user_id}")
            return user_tokens
        
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while creating user token {user_tokens.id} for user {user_tokens.user_id}: {str(e)}")
            # Check if it's a unique constraint violation (though checked above, good practice)
            if "unique constraint" in str(e).lower():
                raise AlreadyExistsError(
                    f"user_id '{user_tokens.user_id}'already exists (concurrent request?)."
                )
            else:
                logger.error(f"Database integrity error for user {user_tokens.user_id}: {str(e)}")
                raise ServerError(f"Database integrity error: {e}") from e
                
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"SQLAlchemy error while creating user_tokens for user: {user_tokens.user_id} : {str(e)}")
            raise ServerError(f"Could not create user: {e}") from e

    
    async def check_if_user_exist_X_id(self, x_id: str):
        result = await self.db.execute(sa.select(User).where(x_id == User.x_id))
        if not result:
            return None
        return result.scalar_one_or_none() 
        # return True if result.scalar_one_or_none() else False
    
    async def check_if_user_exists_user_id(self, user_id:str):
        result = await self.db.execute(sa.select(User).where(user_id == User.id))
        return True if result.scalar_one_or_none() else False
    
    async def fetch_user_token(self, user_id):
        result = await self.db.execute(
            sa.select(UserToken).where(
                user_id = UserToken.user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def is_token_expired(self, user_id):
        result = await self.db.execute(
            sa.select(UserToken).where(
                sa.and_(
                    user_id == UserToken.user_id,
                    UserToken.is_expired == True
                    )
                
                )
            )
        logger.info(type(result))
        return result.scalar_one_or_none()