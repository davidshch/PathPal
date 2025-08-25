"""Database connection and engine configuration."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from ..settings import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
)

# Create session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from . import models  # noqa: F401

        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session():
    """Get async database session context manager."""
    return async_session()
