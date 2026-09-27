from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.utils.session_token import decode_session_token
from source.config import settings
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import fail
from source.enums import EmployeeRole

security = HTTPBearer(auto_error=False)


async def get_current_employee(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> EmployeeOrm:
    if not credentials:
        dev_telegram_id = request.headers.get("X-Dev-Telegram-Id")
        if settings.app.env == "development" and settings.auth.dev_bypass and dev_telegram_id:
            logger.warning("AUTH__DEV_BYPASS used")
            try:
                telegram_id = int(dev_telegram_id)
            except ValueError as exc:
                raise fail("SESSION_EXPIRED", 401) from exc
            employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == telegram_id))
            if not employee:
                raise fail("NOT_REGISTERED", 403)
            if not employee.is_active:
                raise fail("ACCOUNT_LOCKED", 403)
            return employee
        raise fail("SESSION_EXPIRED", 401)
    employee_id = decode_session_token(credentials.credentials)
    employee = await session.get(EmployeeOrm, employee_id)
    if not employee:
        raise fail("NOT_REGISTERED", 403)
    if not employee.is_active:
        raise fail("ACCOUNT_LOCKED", 403)
    return employee


def require_roles(*roles: EmployeeRole) -> Callable:
    async def dependency(employee: EmployeeOrm = Depends(get_current_employee)) -> EmployeeOrm:
        if employee.role not in roles:
            raise fail("FORBIDDEN", 403)
        return employee
    return dependency


employee_only = require_roles(EmployeeRole.employee)
manager_only = require_roles(EmployeeRole.manager)
manager_or_director = require_roles(EmployeeRole.manager, EmployeeRole.director)
