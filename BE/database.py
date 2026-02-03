"""Async SQLAlchemy engine and session factory for PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.logger import setup_logger
from BE.models import Base

logger = setup_logger(__name__)

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        from BE.config import settings

        _engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables if they don't exist."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL tables initialized")


async def get_db() -> AsyncSession:
    """Get an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        return session
