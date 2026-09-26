from aiogram import Router
from aiogram.exceptions import AiogramError
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.types import ErrorEvent
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject
from loguru import logger

from source.utils import I18n

telegram_errors_router = Router(name=__name__)


@telegram_errors_router.error(ExceptionTypeFilter(AiogramError))
@aiogram_inject
async def handle_bad_request(event: ErrorEvent, i18n: FromDishka[I18n]) -> None:
    update = event.update

    if update.message:
        text = await i18n(update.message.from_user.id, "error")
        await update.message.answer(text=text)

    elif update.callback_query:
        text = await i18n(update.callback_query.from_user.id, "error")
        await update.callback_query.answer()
        await update.callback_query.message.answer(text=text)

    logger.error(f"Telegram Error: {event.exception}")
