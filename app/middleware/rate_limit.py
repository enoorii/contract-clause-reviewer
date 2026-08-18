# app/middleware/rate_limit.py
import json
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import setting
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.rate_limiter import RedisRateLimiter


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = setting.RATE_LIMIT_GLOBAL_MAX or 1000,
        window_seconds: int = setting.BRUTE_FORCE_WINDOW_SECONDS or 60,
        exclude_paths: list | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        rate_limiter = RedisRateLimiter(redis_client)

        # Use client IP as key
        client_ip = request.client.host if request.client else "unknown"
        key = f"global:{client_ip}"

        # Infrastructure returns data, middleware handles HTTP response
        is_limited, info = await rate_limiter.is_rate_limited(
            key, self.max_requests, self.window_seconds
        )

        if is_limited:
            return Response(
                content=json.dumps(
                    {
                        "detail": "Too many requests - global limit exceeded",
                        "rate_limit": info,
                    }
                ),
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(time.time())),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response
