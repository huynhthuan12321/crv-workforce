from aiogram import Router

from .commands import user_commands_router
from .keyboard import user_keyboard_router


def setup_user_routers() -> Router:
    router = Router(name=__name__)
    router.include_routers(
        user_commands_router,
        user_keyboard_router,
    )
    return router
