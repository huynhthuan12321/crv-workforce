from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.utils.session_token import create_session_token
from source.api.utils.telegram_auth import validate_init_payload
from source.api.workforce_auth import get_current_employee
from source.config import settings
from source.database.models import EmployeeOrm, InviteCodeOrm
from source.domain.workforce_errors import fail
from source.utils.clock import Clock

router = APIRouter()


class InitDataRequest(BaseModel):
    init_data: str


def _validate(raw: str) -> dict:
    payload = validate_init_payload(
        raw, settings.tg.bot_token.get_secret_value(),
        settings.auth.initdata_max_age_seconds,
    )
    if not payload:
        raise fail("INITDATA_INVALID", 401)
    return payload


def _employee_payload(employee: EmployeeOrm) -> dict:
    tabs = {
        "employee": ["attendance", "outputs", "history"],
        "manager": ["working", "review", "payroll", "employees"],
        "director": ["reports", "review", "payroll"],
    }[employee.role.value]
    return {"id": employee.id, "code": employee.code, "full_name": employee.full_name,
            "role": employee.role.value, "tabs": tabs}


@router.post("/session")
async def create_session(body: InitDataRequest, session: AsyncSession = Depends(get_session)):
    data = _validate(body.init_data)
    telegram_id = int(data["user"]["id"])
    employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == telegram_id))
    if not employee:
        raise fail("NOT_REGISTERED", 403)
    if not employee.is_active:
        raise fail("ACCOUNT_LOCKED", 403)
    return {"data": {"token": create_session_token(employee.id), "employee": _employee_payload(employee)}}


@router.post("/redeem-invite")
async def redeem_invite(body: InitDataRequest, session: AsyncSession = Depends(get_session)):
    data = _validate(body.init_data)
    code = data.get("start_param")
    if not code:
        raise fail("INVITE_INVALID", 422)
    now = Clock().now()
    telegram_id = int(data["user"]["id"])
    async with session.begin():
        already = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == telegram_id))
        if already:
            raise fail("TELEGRAM_ALREADY_LINKED")
        invite = await session.scalar(select(InviteCodeOrm).where(InviteCodeOrm.code == code).with_for_update())
        if not invite:
            raise fail("INVITE_INVALID", 422)
        if invite.used_at:
            raise fail("INVITE_USED")
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=now.tzinfo)
        if expires_at <= now:
            raise fail("INVITE_EXPIRED")
        employee = await session.get(EmployeeOrm, invite.employee_id)
        if not employee or not employee.is_active:
            raise fail("ACCOUNT_LOCKED", 403)
        employee.telegram_id = telegram_id
        employee.telegram_username = data["user"].get("username")
        invite.used_at = now
    return {"data": {"token": create_session_token(employee.id), "employee": _employee_payload(employee)}}


@router.get("/me")
async def me(employee: EmployeeOrm = Depends(get_current_employee)):
    return {"data": _employee_payload(employee)}
