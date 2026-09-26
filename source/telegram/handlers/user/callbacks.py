from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService
from source.utils import I18n

user_callbacks_router = Router(name=__name__)


@user_callbacks_router.callback_query(F.data == "language_ru")
@aiogram_inject
async def language_ru(
    callback: CallbackQuery,
    i18n: FromDishka[I18n],
    user_service: FromDishka[UserService],
) -> None:
    user = callback.from_user

    await callback.answer("")
    await user_service.update_user(user.id, {"language_code": "ru"})
    i18n.invalidate_cache(user.id)

    changed_language = await i18n(user.id, "language-name-ru")
    text = await i18n(user.id, "changed_language", language=changed_language)

    await callback.message.delete()
    await callback.message.answer(text=text)


@user_callbacks_router.callback_query(F.data == "language_en")
@aiogram_inject
async def language_en(
    callback: CallbackQuery,
    i18n: FromDishka[I18n],
    user_service: FromDishka[UserService],
) -> None:
    user = callback.from_user

    await callback.answer("")
    await user_service.update_user(user.id, {"language_code": "en"})
    i18n.invalidate_cache(user.id)

    changed_language = await i18n(user.id, "language-name-en")
    text = await i18n(user.id, "changed_language", language=changed_language)

    await callback.message.delete()
    await callback.message.answer(text=text)
