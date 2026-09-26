from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.utils.session_token import create_session_token
from source.api.utils.telegram_auth import validate_init_payload
from source.api.workforce_auth import get_current_employee
from source.config import settings
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import fail
from source.services.workforce import AuthService, employee_payload

router = APIRouter()


class InitDataRequest(BaseModel):
    init_data: str


def _validate(raw: str) -> dict:
    return validate_init_payload(
        raw, settings.tg.bot_token.get_secret_value(),
        settings.auth.initdata_max_age_seconds,
    )


@router.post("/session")
async def create_session(body: InitDataRequest, session: AsyncSession = Depends(get_session)):
    data = _validate(body.init_data)
    telegram_id = int(data["user"]["id"])
    employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == telegram_id))
    if not employee:
        raise fail("NOT_REGISTERED", 403)
    if not employee.is_active:
        raise fail("ACCOUNT_LOCKED", 403)
    return {"data": {"token": create_session_token(employee.id),
                     "employee": await employee_payload(session, employee)}}


@router.post("/redeem-invite")
async def redeem_invite(body: InitDataRequest, session: AsyncSession = Depends(get_session)):
    data = _validate(body.init_data)
    async with session.begin():
        employee = await AuthService(session).redeem_invite(data)
    return {"data": {"token": create_session_token(employee.id),
                     "employee": await employee_payload(session, employee)}}


@router.get("/me")
async def me(employee: EmployeeOrm = Depends(get_current_employee), session: AsyncSession = Depends(get_session)):
    return {"data": await employee_payload(session, employee)}
