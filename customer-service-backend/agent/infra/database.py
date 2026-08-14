import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agent.conf.settings import settings

logger = logging.getLogger(__name__)
logger.info(f"LOADING DATABASE MODULE: {__file__}, {id(sys.modules[__name__])}")

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine() -> None:
    global engine, session_factory

    engine = create_async_engine(
        settings.database_url,
        # echo=True,               # Log all SQL statements; enable in dev, disable in prod
        # echo_pool=True,          # Log connection pool events
        pool_size=5,             # Maximum number of permanent connections in the pool
        max_overflow=10,         # Maximum number of connections allowed beyond pool_size, block and timeout if exhausted
        pool_recycle=3600,       # Recycle connections after 1 hour to prevent stale connections
        pool_pre_ping=True       # Verify connections before checkout (SELECT 1); reconnect if dropped
    )
    logger.info(f"Database engine initialized: {engine}")
    
    # NOTE: expire_on_commit must be set to False for async sessions
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.info(f"Session factory initialized: {session_factory}")


async def close_db_engine():
    if engine is not None:
        await engine.dispose()
        logger.info(f"Database engine {engine} disposed...")

logger.info(f"DATABASE MODULE LOADED: {__file__}, {id(sys.modules[__name__])}")