
from aiogram import Router
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog import StartMode
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService
from source.telegram.keyboards import get_profile_webapp_keyboard
from source.telegram.keyboards import inline_language_kb
from source.telegram.states import DialogSG
from source.telegram.states import FormSG
from source.utils import I18n

user_commands_router = Router(name=__name__)


@user_commands_router.message(CommandStart())
@aiogram_inject
async def start(
    message: Message,
    user_service: FromDishka[UserService],
    i18n: FromDishka[I18n],
) -> None:
    user = message.from_user
    await user_service.register_user(user.id)
    greeting = await i18n(user.id, "greeting", mention=user.full_name)
    await message.answer(greeting)


@user_commands_router.message(Command("help"))
@aiogram_inject
async def help_command(message: Message, i18n: FromDishka[I18n]) -> None:
    text = await i18n(message.from_user.id, "help")
    await message.answer(text)


@user_commands_router.message(Command("language"))
@aiogram_inject
async def language(message: Message, i18n: FromDishka[I18n]) -> None:
    user = message.from_user
    text = await i18n(user.id, "change_language")
    await message.reply(text=text, reply_markup=inline_language_kb)


@user_commands_router.message(Command("dialog"))
async def dialog_command(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(DialogSG.first, mode=StartMode.RESET_STACK)


@user_commands_router.message(Command("fsm"))
@aiogram_inject
async def start_form(
    message: Message, state: FSMContext, i18n: FromDishka[I18n]
) -> None:
    await state.set_state(FormSG.name)
    await message.answer(await i18n(message.from_user.id, "fsm-enter-name"))


@user_commands_router.message(Command("profile"))
@aiogram_inject
async def profile_command(
    message: Message,
    user_service: FromDishka[UserService],
    i18n: FromDishka[I18n],
) -> None:
    await user_service.register_user(message.from_user.id)
    text = await i18n(message.from_user.id, "profile-intro")
    button_text = await i18n(message.from_user.id, "profile-open-button")
    await message.answer(
        text,
        reply_markup=get_profile_webapp_keyboard(button_text),
    )
