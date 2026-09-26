from aiogram import Router

from .dialog import dialog


def setup_dialog_routers() -> Router:
    router = Router(name=__name__)
    router.include_router(dialog)
    return router
