import time
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from prometheus_client import Counter
from prometheus_client import Histogram

telegram_requests_total = Counter(
    "telegram_requests_total",
    "Total telegram requests",
    ["handler", "status"],
)

telegram_request_duration = Histogram(
    "telegram_request_duration_seconds",
    "Request duration in seconds",
    ["handler"],
)


class PrometheusMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        handler_name = getattr(handler, "__name__", "unknown")
        start_time = time.monotonic()
        try:
            result = await handler(event, data)
            telegram_requests_total.labels(handler=handler_name, status="success").inc()
            return result
        except Exception:
            telegram_requests_total.labels(handler=handler_name, status="error").inc()
            raise
        finally:
            duration = time.monotonic() - start_time
            telegram_request_duration.labels(handler=handler_name).observe(duration)
