"""Database module for the FastAPI application"""

from collections.abc import AsyncGenerator

from config import settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.debug)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Async generator for getting a session"""
    async with async_session() as session:
        yield session
