import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.api.routers.chat_router import router as chat_router
from agent.api.routers.health_router import router as health_router
from agent.conf.settings import settings
from agent.engine.singleton import build_dialogue_engine
from agent.infra.database import close_db_engine, init_db_engine
from agent.infra.http_client import close_http_client, init_http_client

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("App startup...")
    init_db_engine()
    init_http_client()
    # 组合根在启动期构建，fail-fast：yml/action 边界校验失败则进程直接起不来，
    # 而非等到首个请求才 500。实例挂在 app.state，而非模块级全局（避免并发竞态与测试污染）。
    app.state.dialogue_engine = build_dialogue_engine()

    yield

    await close_db_engine()
    await close_http_client()
    logger.info("App shutdown...")


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description, 
    lifespan=lifespan)

app.include_router(chat_router)
app.include_router(health_router)