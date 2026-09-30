# app/infrastructure/redis/dependencies.py
import time
from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import ActiveUser, AdminUser, CurrrentUser
from app.infrastructure.logging import get_logger
from app.infrastructure.redis.client import RDClient
from app.infrastructure.redis.rate_limiter import RedisRateLimiter

logger = get_logger(__name__)

# ============ Core Rate Limit Function ============


async def check_rate_limit(
    request: Request,
    redis: RDClient,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> dict:
    """
    Core rate limit checking function.
    Raises HTTP 429 if rate limit is exceeded.
    This is in the API layer, so HTTP exceptions are appropriate.
    """
    rate_limiter = RedisRateLimiter(redis_client=redis)
    is_limited, info = await rate_limiter.is_rate_limited(
        key=key, max_requests=max_requests, window_seconds=window_seconds
    )

    if is_limited:
        logger.error(
            "rate limit for request with ip: %s",
            request.client.host if request.client is not None else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": "Too many requests", "rate_limit": info},
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(info["reset"] - int(time.time())),
            },
        )

    return info


# ============ Specific Rate Limiters ============
#
# IMPORTANT: Limiters only perform a rate-limit check. They do NOT return
# the user. If an endpoint needs the user, it should declare
# `CurrrentUser` / `ActiveUser` / `AdminUser` in its own signature.
#
# FastAPI's dependency cache guarantees the user is resolved at most once
# per request, even if it's declared here AND in the endpoint body.


async def user_limiter(
    request: Request,
    user: CurrrentUser,
    redis: RDClient,
) -> str:
    """Rate limiter for authenticated user endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"user:{user.id}:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=60,
        window_seconds=60,
    )
    return "ok"


async def admin_limiter(
    request: Request,
    user: AdminUser,
    redis: RDClient,
) -> str:
    """Rate limiter for admin endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"admin:{user.id}:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=100,
        window_seconds=60,
    )
    return "ok"


async def active_user_limiter(
    request: Request,
    user: ActiveUser,
    redis: RDClient,
) -> str:
    """Rate limiter for active-user endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"user:{user.id}:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=60,
        window_seconds=60,
    )
    return "ok"


async def analysis_limiter(
    request: Request,
    user: ActiveUser,
    redis: RDClient,
) -> str:
    """Rate limiter for analysis endpoints (stricter limit)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"analysis:{user.id}:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=10,
        window_seconds=60,
    )
    return "ok"


async def general_limiter(
    request: Request,
    redis: RDClient,
) -> str:
    """Rate limiter for public endpoints (by IP only)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"public:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=60,
        window_seconds=60,
    )
    return "ok"


async def login_limiter(
    request: Request,
    redis: RDClient,
) -> str:
    """Special rate limiter for login endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"login:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=10,
        window_seconds=60,
    )
    return "ok"


# ============ Flexible Factory Function ============


def create_rate_limiter(
    max_requests: Optional[int] = None,
    window_seconds: Optional[int] = None,
    key_prefix: str = "custom",
    include_user: bool = False,
    include_ip: bool = True,
) -> Callable:
    """
    Factory to create custom rate limiter dependencies.

    Usage:
        @router.get("/custom")
        async def endpoint(
            rate_limit: Annotated[dict, Depends(create_rate_limiter(10, 30))]
        ):
            ...
    """

    async def rate_limiter_dependency(
        request: Request,
        redis: RDClient,
        user: Optional[ActiveUser] = None,
    ) -> dict:
        key_parts = [key_prefix]

        if include_user and user:
            key_parts.append(str(user.id))

        if include_ip:
            client_ip = request.client.host if request.client else "unknown"
            key_parts.append(client_ip)

        key = ":".join(key_parts)

        req_limit = max_requests or 60
        window = window_seconds or 60

        return await check_rate_limit(request, redis, key, req_limit, window)

    return rate_limiter_dependency


# ============ Pre-configured Rate Limiters ============
#
# All of these resolve to `str` (a placeholder) — they exist to trigger the
# rate-limit check. Pair them with `CurrrentUser` / `ActiveUser` / `AdminUser`
# if the endpoint also needs the user.

UserRateLimit = Annotated[str, Depends(user_limiter)]
AdminRateLimit = Annotated[str, Depends(admin_limiter)]
ActiveUserRateLimit = Annotated[str, Depends(active_user_limiter)]

ActiveUserAnalysisRateLimit = Annotated[str, Depends(analysis_limiter)]

PublicRateLimit = Annotated[str, Depends(general_limiter)]

LoginRateLimit = Annotated[str, Depends(login_limiter)]


# For endpoints with custom limits and testing
async def rate_limit_10_per_minute(
    request: Request,
    redis: RDClient,
) -> str:
    """Rate limiter for public endpoints (by IP only)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"test:{client_ip}"

    await check_rate_limit(
        request=request,
        redis=redis,
        key=key,
        max_requests=10,
        window_seconds=60,
    )
    return "ok"


RateLimit10PerMinute = Annotated[str, Depends(rate_limit_10_per_minute)]
