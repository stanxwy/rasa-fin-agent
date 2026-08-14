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

if __name__ == '__main__':
    from sqlalchemy import text

    async def test():
        init_db_engine()

        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            data = result.fetchone()
            print(data)
            print(type(data))
            await session.commit()

        await close_db_engine()

    asyncio.run(test())

"""
python -m agent.infra.database
get_settings will be called only once...
2026-08-04 19:18:38,076 INFO sqlalchemy.engine.Engine SELECT DATABASE()
2026-08-04 19:18:38,077 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-08-04 19:18:38,079 INFO sqlalchemy.engine.Engine SELECT @@sql_mode
2026-08-04 19:18:38,080 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-08-04 19:18:38,082 INFO sqlalchemy.engine.Engine SELECT @@lower_case_table_names
2026-08-04 19:18:38,082 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-08-04 19:18:38,084 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-08-04 19:18:38,085 INFO sqlalchemy.engine.Engine SELECT 1
2026-08-04 19:18:38,086 INFO sqlalchemy.engine.Engine [generated in 0.00024s] ()
(1,)
<class 'sqlalchemy.engine.row.Row'>
2026-08-04 19:18:38,087 INFO sqlalchemy.engine.Engine COMMIT
2026-08-04 19:18:38,089 INFO sqlalchemy.pool.impl.AsyncAdaptedQueuePool Pool disposed. Pool size: 5  Connections in pool: 0 Current Overflow: -5 Current Checked out connections: 0
2026-08-04 19:18:38,089 INFO sqlalchemy.pool.impl.AsyncAdaptedQueuePool Pool recreating
"""