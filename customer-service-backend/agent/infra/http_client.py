import asyncio

import httpx

_TIMEOUT_SECS = 10.0

# 全局变量
http_client: httpx.AsyncClient | None = None

# 初始化http客户端
def init_http_client():
    global http_client
    http_client = httpx.AsyncClient(timeout=_TIMEOUT_SECS)

# 关闭资源
async def close_http_client():
    if http_client is not None:
        await http_client.aclose()