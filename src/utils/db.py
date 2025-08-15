from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import config
from src.v1.base.model import Base, BaseModel
from src.v1 import model
from .config import config
from sqlalchemy.exc import SQLAlchemyError
from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="error.log")

engine = create_async_engine(url= config.DATABASE_URL)

async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates and yields an asynchronous database session.

    This function is an asynchronous generator that creates a new database session
    using the async_session factory and yields it. The session is automatically
    closed when the generator is exhausted or the context is exited.

    Yields:
        AsyncSession: An asynchronous SQLAlchemy session object.

    Usage:
        async for session in get_session():
            # Use the session for database operations
            ...
    """
    async with async_session() as session:
        yield session
        
# for manual use (not in fastapi Dependency injection, normal class/func injection)
async def get_manual_db_session() -> AsyncSession:
    async with async_session() as session:
        return session


async def init_db():
    """
    Initialize the database by creating all tables defined in the Base metadata.

    This asynchronous function uses the SQLAlchemy engine to create all tables
    that are defined in the Base metadata. It's typically used when setting up
    the database for the first time or after a complete reset.

    The function uses a connection from the engine and runs the create_all
    method synchronously within the asynchronous context.
    """
    try:
        async with engine.begin() as conn:
            # Use run_sync to call the synchronous create_all method in an async context
            await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as e:
        logger.error(f"error creating the db: {e}")


async def drop_db():
    """
    Drop all tables in the database.

    This asynchronous function uses the SQLAlchemy engine to drop all tables
    that are defined in the Base metadata. It's typically used when you want
    to completely reset the database structure.

    Caution: This operation will delete all data in the tables. Use with care.
    """
    async with engine.begin() as conn:
        # Use run_sync to call the synchronous drop_all method in an async context
        await conn.run_sync(Base.metadata.drop_all)

