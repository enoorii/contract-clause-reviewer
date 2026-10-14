# app/middleware/request_log.py
from time import perf_counter

from fastapi import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.logging import (
    log_request_completed,
    log_request_error,
    log_request_start,
)


class RequestLogMiddleware:
    """
    Pure ASGI middleware for request logging.

    Advantages over BaseHTTPMiddleware:
    - No extra asyncio task creation/scheduling
    - No memory object streams
    - No full response streaming wrapper

    Note: we still construct a lightweight `Request` object so the logging
    layer's API stays unchanged. This is cheap — `Request` is just a thin
    wrapper around `scope` and `receive`.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

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

        start = perf_counter()

        # Build a lightweight Request from the ASGI scope + receive.
        request = Request(scope, receive=receive)

        # Captured response info (populated by send_wrapper)
        status_code: int | None = None
        response_headers: list[tuple[bytes, bytes]] | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
            await send(message)

        log_request_start(request)

        try:
            await self.app(scope, receive, send_wrapper)
            duration = perf_counter() - start

            log_request_completed(request, status_code or 500, duration)
        except Exception as exc:
            duration = perf_counter() - start
            log_request_error(request, exc, duration)
            raise
