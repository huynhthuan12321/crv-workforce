from aiogram import Dispatcher

from .errors import setup_errors_routers
from .user import setup_user_routers


def setup_routers(dp: Dispatcher) -> Dispatcher:
    dp.include_routers(
        setup_user_routers(),
        setup_errors_routers(),
    )
    return dp
