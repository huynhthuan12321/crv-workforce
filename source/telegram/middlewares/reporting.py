import traceback

from aiogram import BaseMiddleware
from aiogram import Bot
from aiogram.types import ErrorEvent
from collections.abc import Awaitable
from collections.abc import Callable
from loguru import logger
from typing import Any


class ErrorReportingMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[ErrorEvent, dict[str, Any]], Awaitable[Any]],
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> Any:
        try:
            error_message = f"An error occurred:: {event.exception}"

            traceback_info = traceback.format_exc()
            shortened_traceback = "\n".join(traceback_info.splitlines()[-5:])

            details = f"Details:\n\n{shortened_traceback}"
            full_message = f"{error_message}\n\n{details}"

            bot: Bot = data["bot"]
            for admin_id in self.admin_ids:
                await bot.send_message(admin_id, full_message)

        except Exception as e:
            logger.error(e)

        return await handler(event, data)
