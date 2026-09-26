from aiogram import F
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message

user_messages_router = Router(name=__name__)


@user_messages_router.message(F.text, StateFilter(None))
async def echo(message: Message) -> None:
    await message.answer(message.text)
