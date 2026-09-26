from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import WebAppInfo

from source.config import settings


def get_profile_webapp_keyboard(
    text: str = "👤 Открыть профиль",
) -> InlineKeyboardMarkup:
    """Keyboard with a WebApp profile button."""
    base_url = settings.webapp.url.rstrip("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{base_url}/profile"))]
        ]
    )


def get_webapp_keyboard(url: str, text: str = "Открыть") -> InlineKeyboardMarkup:
    """Universal keyboard for a WebApp link."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
    )
