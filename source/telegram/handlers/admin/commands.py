from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService
from source.utils import I18n

admin_commands_router = Router(name=__name__)


@admin_commands_router.message(Command("admin"))
@aiogram_inject
async def admin_command(
    message: Message,
    user_service: FromDishka[UserService],
    i18n: FromDishka[I18n],
) -> None:
    user = message.from_user
    await user_service.register_user(user.id)
    text = await i18n(user.id, "admin", mention=user.full_name)
    await message.answer(text)
