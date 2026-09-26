from aiogram.filters import Filter
from aiogram.types import Message

from source.config import settings


class AdminProtectFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in settings.tg.admin_ids
