"""Async SQLAlchemy engine and session factory for PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.logger import setup_logger
from BE.models import Base

logger = setup_logger(__name__)

__all__ = ["get_session_factory", "init_db", "dispose_engine"]

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        from BE.config import settings

        _engine = create_async_engine(
            settings.POSTGRES_URL,
            echo=False,
            pool_size=settings.POSTGRES_POOL_SIZE,
            max_overflow=settings.POSTGRES_MAX_OVERFLOW,
            pool_recycle=settings.POSTGRES_POOL_RECYCLE,
            pool_pre_ping=settings.POSTGRES_POOL_PRE_PING,
        )
        logger.debug(
            "Created async engine with pool_size=%d, max_overflow=%d",
            settings.POSTGRES_POOL_SIZE,
            settings.POSTGRES_MAX_OVERFLOW,
        )
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


async def dispose_engine() -> None:
    """Dispose the async engine, releasing all pooled connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("PostgreSQL engine disposed")
