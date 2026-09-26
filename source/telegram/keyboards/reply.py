from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup

reply_language_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Русский"), KeyboardButton(text="English")],
    ],
    resize_keyboard=True,
)
