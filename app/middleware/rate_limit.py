# app/middleware/rate_limit.py
import json
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import setting
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.rate_limiter import RedisRateLimiter


class GlobalRateLimitMiddleware:
    """
    Pure ASGI rate-limiting middleware.

    Key advantages over BaseHTTPMiddleware:
    - Rejected requests never enter the routing / validation pipeline.
    - No per-request task creation or memory object streams.
    - The RedisRateLimiter instance is created once at startup, not per request.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = setting.RATE_LIMIT_GLOBAL_MAX or 1000,
        window_seconds: int = setting.BRUTE_FORCE_WINDOW_SECONDS or 60,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/docs"]

        # Created once. The rate limiter is stateless beyond its redis client,
        # so there is no reason to instantiate it per request.
        self.rate_limiter = RedisRateLimiter(redis_client)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        # Pass through non-HTTP scopes (lifespan, websocket)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip rate limiting for excluded paths
        if scope["path"] in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Client IP: scope["client"] is a (host, port) tuple or None
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        key = f"global:{client_ip}"

        is_limited, info = await self.rate_limiter.is_rate_limited(
            key, self.max_requests, self.window_seconds
        )

        if is_limited:
            await self._send_429(send, info)
            return

        # Wrap send to inject rate-limit headers into the response.
        # ASGI headers are list[tuple[bytes, bytes]], lowercase names.
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(info["limit"]).encode("latin-1")),
                        (
                            b"x-ratelimit-remaining",
                            str(info["remaining"]).encode("latin-1"),
                        ),
                        (b"x-ratelimit-reset", str(info["reset"]).encode("latin-1")),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_429(self, send: Send, info: dict) -> None:
        """Send a complete ASGI 429 response without invoking downstream."""
        body = json.dumps(
            {
                "detail": "Too many requests - global limit exceeded",
                "rate_limit": info,
            }
        ).encode("utf-8")

        # Clamp to 0 — a negative Retry-After is meaningless.
        retry_after = max(0, info["reset"] - int(time.time()))

        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                    (b"x-ratelimit-limit", str(info["limit"]).encode("latin-1")),
                    (
                        b"x-ratelimit-remaining",
                        str(info["remaining"]).encode("latin-1"),
                    ),
                    (b"x-ratelimit-reset", str(info["reset"]).encode("latin-1")),
                    (b"retry-after", str(retry_after).encode("latin-1")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
