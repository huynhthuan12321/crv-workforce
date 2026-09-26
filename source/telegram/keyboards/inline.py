from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

inline_language_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="language_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="language_en")],
    ],
)
