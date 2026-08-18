# app/infrastructure/redis/client.py
from typing import Annotated

import redis.asyncio as async_redis
from fastapi import Depends

from app.core.config import setting

# ==================== FastAPI (Async) Redis ====================

redis_client = async_redis.from_url(
    setting.redis_url,
    max_connections=setting.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
    encoding="utf-8",
    socket_timeout=setting.REDIS_SOCKET_TIMEOUT or 5,
    socket_connect_timeout=setting.REDIS_SOCKET_CONNECT_TIMEOUT or 5,
    retry_on_timeout=True,
)


async def get_async_redis():
    yield redis_client


RDClient = Annotated[async_redis.Redis, Depends(get_async_redis)]
