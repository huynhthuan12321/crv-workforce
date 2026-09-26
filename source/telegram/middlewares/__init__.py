from aiogram import Dispatcher

from source.constants import ThrottlingConstants as const
from .auth import AuthMiddleware as AuthMiddleware
from .base import BaseAppMiddleware as BaseAppMiddleware
from .reporting import ErrorReportingMiddleware as ErrorReportingMiddleware
from .throttling import ThrottlingMiddleware as ThrottlingMiddleware
from source.config import settings

__all__ = [
    "AuthMiddleware",
    "BaseAppMiddleware",
    "ErrorReportingMiddleware",
    "ThrottlingMiddleware",
    "setup_middlewares",
]


def setup_middlewares(dp: Dispatcher) -> Dispatcher:
    dp.error.middleware(ErrorReportingMiddleware(settings.tg.admin_ids))
    dp.message.middleware(ThrottlingMiddleware(const.message_time_limit))
    dp.callback_query.middleware(ThrottlingMiddleware(const.callback_time_limit))
    return dp
