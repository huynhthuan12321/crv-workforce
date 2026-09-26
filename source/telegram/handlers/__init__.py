from aiogram import Dispatcher

from ..dialogs import setup_dialog_routers
from .admin import setup_admin_routers
from .errors import setup_errors_routers
from .user import setup_user_routers
from .webapp import setup_webapp_routers


def setup_routers(dp: Dispatcher) -> Dispatcher:
    dp.include_routers(
        setup_admin_routers(),
        setup_user_routers(),
        setup_webapp_routers(),
        setup_errors_routers(),
        setup_dialog_routers(),
    )
    return dp
