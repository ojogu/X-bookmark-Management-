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
        x_id = user_data["id"]
        logger.info(f"Attempting to create user with x_id: {x_id}")
        
        is_user = self.check_if_user_exist_X_id(x_id)
        if is_user:
            logger.warning(f"User creation failed - x_id {x_id} already exists")
            raise AlreadyExistsError(f"user with id: {x_id} already exist")
            
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
                raise DatabaseError(f"Database integrity error: {e}") from e
                
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"SQLAlchemy error while creating user {x_id}: {str(e)}")
            raise DatabaseError(f"Could not create user: {e}") from e

    async def store_user_token(self, user_id:str, user_token:dict):
        pass 
    
    async def check_if_user_exist_X_id(self, x_id: str):
        result = await self.db.execute(sa.select(User).where(x_id == User.x_id))
        return True if result.scalar_one_or_none() else False
    
    async def check_if_user_exists_user_id(self, user_id:str):
        result = await self.db.execute(sa.select(UserToken).where(user_id == UserToken.user_id))
        return True if result.scalar_one_or_none() else False