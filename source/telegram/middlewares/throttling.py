from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.types import TelegramObject
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, time_limit: int, maxsize: int = 10_000) -> None:
        self._cache = TTLCache(maxsize=maxsize, ttl=time_limit)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        if user_id in self._cache:
            message = "Please wait before your next action."
            i18n = data.get("i18n")
            if i18n is not None:
                message = await i18n(user_id, "throttling")
            if isinstance(event, CallbackQuery):
                await event.answer(message)
            elif isinstance(event, Message):
                await event.answer(message)
            return None

        self._cache[user_id] = True
        return await handler(event, data)
