from aiogram import Router

from .callbacks import webapp_callbacks_router


def setup_webapp_routers() -> Router:
    router = Router(name=__name__)
    router.include_router(webapp_callbacks_router)
    return router
