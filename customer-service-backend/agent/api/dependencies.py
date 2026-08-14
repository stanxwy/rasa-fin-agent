import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent.engine.dialogue_engine import DialogueEngine
from agent.infra import database
from agent.repository.dialogue_state_repo import DialogueStateRepository
from agent.service.dialogue_service import DialogueService

logger = logging.getLogger(__name__)

async def get_session() -> AsyncGenerator[AsyncSession]:
    # logger.info(f"SESSION FACTORY ID: {id(session_factory)}, value: {session_factory}") 
    # session_factory will be None if 'from agent.infra.database import session_factory' is used
    """
    Dependency that provides an AsyncSession.

    Execution flow:
        1. Enter async with -> open a new database session
        2. Yield the session -> injected into repositories / services
        3. Route handler finishes execution
        4. Resume after yield -> session is automatically closed

    :return: AsyncSession
    """
    # NOTE: Always use `database.session_factory()` instead of
    # `from agent.infra.database import session_factory`.
    #
    # `from ... import session_factory` captures the value at import time.
    # If this module is imported before `init_db_engine()` runs,
    # session_factory will remain None forever, even after initialization.
    #
    # Accessing it via `database.session_factory` ensures we always read
    # the current module-level value.
    async with database.session_factory() as session:
        logger.info("Open database session...")

        yield session

        logger.info("Close database session...")


def get_dialogue_state_repository(
    session: AsyncSession = Depends(get_session)
) -> DialogueStateRepository:
    """
    Factory dependency that creates a DialogueStateRepository.

    Dependency resolution order:
        1. get_session() opens a session and yields it
        2. This dependency receives the session and instantiates the repository
        3. The repository is consumed by services, which are used by route handlers
        4. Once the request completes, get_session() resumes and closes the session

    :param session: Injected AsyncSession from get_session()
    :return: DialogueStateRepository instance
    """
    return DialogueStateRepository(session=session)


def get_dialogue_engine(request: Request) -> DialogueEngine:
    """
    从 lifespan 启动期构建并挂在 app.state 上的 engine 实例获取。

    不再走模块级懒加载单例（曾有并发竞态、全局状态污染测试、fail-late 等隐患）；
    engine 在应用启动时已由 lifespan 构建并校验，请求期直接读取即可。
    """
    return request.app.state.dialogue_engine


def get_dialogue_service(
    dialogue_state_repo: DialogueStateRepository = Depends(get_dialogue_state_repository),
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine)
) -> DialogueService:
    return DialogueService(
        dialogue_state_repo=dialogue_state_repo, 
        dialogue_engine=dialogue_engine)