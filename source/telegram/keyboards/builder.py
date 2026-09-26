from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def inline_keyboard_builder(
    buttons: str | list[str],
    callback: str | list[str],
    locale: str = "ru",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    buttons = [buttons] if isinstance(buttons, str) else buttons
    callback = [callback] if isinstance(callback, str) else callback

    for text, data in zip(buttons, callback, strict=False):
        builder.button(text=text, callback_data=data)

    return builder.adjust(2).as_markup()
