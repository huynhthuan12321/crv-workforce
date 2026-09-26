import json

from aiogram import F
from aiogram import Router
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService

webapp_callbacks_router = Router(name=__name__)


@webapp_callbacks_router.message(F.web_app_data)
@aiogram_inject
async def handle_webapp_data(
    message: Message,
    user_service: FromDishka[UserService],
) -> None:
    """Handle data sent from WebApp."""
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка обработки данных")
        return

    action = data.get("action")
    if action == "bio_updated":
        new_bio = data.get("bio")
        await user_service.update_bio(message.from_user.id, new_bio)
        await message.answer("✅ Биография успешно обновлена!")
    elif action == "profile_viewed":
        pass
