from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_only
from source.database.models import EmployeeOrm, RateHistoryOrm, WorkSessionOrm
from source.domain.workforce_errors import fail
from source.enums import SessionStatus
from source.services.workforce import create_employee, create_invite

router = APIRouter()


class EmployeeBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=2, max_length=200)
    hourly_rate: int = Field(gt=0)
    effective_from: date


class RateBody(BaseModel):
    hourly_rate: int = Field(gt=0)
    effective_from: date


def employee_data(row: EmployeeOrm) -> dict:
    return {"id": row.id, "code": row.code, "full_name": row.full_name,
            "role": row.role.value, "telegram_id": row.telegram_id, "is_active": row.is_active}


@router.get("")
async def employees(_: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(EmployeeOrm).order_by(EmployeeOrm.full_name))).all()
    return {"data": [employee_data(x) for x in rows]}


@router.post("")
async def add(body: EmployeeBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        employee, invite = await create_employee(session, actor, body.code, body.full_name, body.hourly_rate, body.effective_from)
    return {"data": {**employee_data(employee), "invite_url": invite}}


@router.post("/{employee_id}/lock")
async def lock(employee_id: int, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await session.get(EmployeeOrm, employee_id)
        opened = await session.scalar(select(WorkSessionOrm.id).where(WorkSessionOrm.employee_id == employee_id, WorkSessionOrm.status == SessionStatus.open))
        if not row or opened:
            raise fail("EMPLOYEE_HAS_OPEN_SESSION")
        row.is_active = False
    return {"data": employee_data(row)}


@router.post("/{employee_id}/unlock")
async def unlock(employee_id: int, _: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await session.get(EmployeeOrm, employee_id)
        if not row:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        row.is_active = True
    return {"data": employee_data(row)}


@router.post("/{employee_id}/invite")
async def regenerate_invite(employee_id: int, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await session.get(EmployeeOrm, employee_id)
        if not row:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        if row.telegram_id:
            return {"data": {**employee_data(row), "invite_url": None}}
        invite = await create_invite(session, row, actor.id)
    return {"data": {**employee_data(row), "invite_url": invite}}


@router.get("/{employee_id}/rates")
async def rates(employee_id: int, _: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(RateHistoryOrm).where(RateHistoryOrm.employee_id == employee_id).order_by(RateHistoryOrm.effective_from.desc()))).all()
    return {"data": [{"id": x.id, "hourly_rate": x.hourly_rate, "effective_from": x.effective_from} for x in rows]}


@router.post("/{employee_id}/rates")
async def add_rate(employee_id: int, body: RateBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    if body.effective_from < date.today():
        raise fail("RATE_DATE_IN_PAST", 422)
    async with session.begin():
        row = RateHistoryOrm(employee_id=employee_id, hourly_rate=body.hourly_rate,
                             effective_from=body.effective_from, created_by=actor.id)
        session.add(row)
    return {"data": {"hourly_rate": row.hourly_rate, "effective_from": row.effective_from}}
