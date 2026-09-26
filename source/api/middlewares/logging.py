import time
from typing import Callable

from fastapi import Request
from fastapi import Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/api/health"):
            return await call_next(request)

        start_time = time.time()

        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip and request.client:
            client_ip = request.client.host

        response = await call_next(request)

        process_time = time.time() - start_time

        logger.info(
            "{method} {path} | status={status} | duration={duration:.3f}s | ip={ip}",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=process_time,
            ip=client_ip or "unknown",
        )

        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
