from aiogram import Router

from .callbacks import admin_callbacks_router
from .commands import admin_commands_router
from .fsm import admin_fsm_router
from .messages import admin_messages_router
from source.telegram.filters import AdminProtectFilter


def setup_admin_routers() -> Router:
    router = Router(name=__name__)
    router.message.filter(AdminProtectFilter())
    router.include_routers(
        admin_callbacks_router,
        admin_commands_router,
        admin_messages_router,
        admin_fsm_router,
    )
    return router
