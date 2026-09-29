from aiogram import Router

from .commands import user_commands_router
from .keyboard import user_keyboard_router
from .callbacks import user_callbacks_router
from .messages import user_messages_router


def setup_user_routers() -> Router:
    router = Router(name=__name__)
    router.include_routers(
        user_commands_router,
        user_keyboard_router,
        user_callbacks_router,
        user_messages_router,
    )
    return router
