# app/middleware/request_log.py
from time import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.logging import (
    log_request_completed,
    log_request_error,
    log_request_start,
)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time()

        log_request_start(request)

        try:
            response = await call_next(request)
            duration = time() - start
            log_request_completed(request, response, duration)
            return response
        except Exception as e:
            duration = time() - start
            log_request_error(request, e, duration)
            raise
