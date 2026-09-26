from aiogram.filters import Filter
from aiogram.types import Message


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: list[str]) -> None:
        self.chat_type = chat_type

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in self.chat_type
