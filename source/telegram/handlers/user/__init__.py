from aiogram import Router

from .callbacks import user_callbacks_router
from .commands import user_commands_router
from .fsm import user_fsm_router
from .messages import user_messages_router


def setup_user_routers() -> Router:
    router = Router(name=__name__)
    router.include_routers(
        user_callbacks_router,
        user_commands_router,
        user_messages_router,
        user_fsm_router,
    )
    return router
