from aiogram import Router

from .commands import user_commands_router


def setup_user_routers() -> Router:
    router = Router(name=__name__)
    router.include_routers(
        user_commands_router,
    )
    return router
