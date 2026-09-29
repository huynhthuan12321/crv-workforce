from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_only
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, EmployeeLocationAssignmentOut, EmployeeOut
from source.services.workforce import EmployeeService

router = APIRouter()


class EmployeeBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=2, max_length=200)
    hourly_rate: int = Field(gt=0)
    effective_from: date | None = None
    location_id: int | None = None
    reason: str | None = Field(default="Đơn giá ban đầu", min_length=5, max_length=200)


class RateBody(BaseModel):
    hourly_rate: int = Field(gt=0)
    mode: Literal["next_shift", "date"] = "next_shift"
    effective_date: date | None = None
    effective_from: date | None = None
    reason: str = Field(min_length=5, max_length=200)
    confirm_large_change: bool = False


class RateCancelBody(BaseModel):
    reason: str = Field(min_length=5, max_length=200)


@router.get("", response_model=DataResponse[list[EmployeeOut]])
async def employees(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    active: bool | None = Query(default=None),
    _: EmployeeOrm = Depends(manager_only),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await EmployeeService(session).list_employees(q=q, active=active)}


@router.post("")
async def add(body: EmployeeBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).create(actor, body.code, body.full_name, body.hourly_rate, body.effective_from, body.location_id, body.reason)}


@router.get("/{employee_id}", response_model=DataResponse[EmployeeOut])
async def employee_detail(employee_id: int, _: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).get(employee_id)}


@router.get("/{employee_id}/location-history", response_model=DataResponse[list[EmployeeLocationAssignmentOut]])
async def location_history(employee_id: int, _: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).location_history(employee_id)}


@router.post("/{employee_id}/lock", response_model=DataResponse[EmployeeOut])
async def lock(employee_id: int, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).lock(actor, employee_id)}


@router.post("/{employee_id}/unlock", response_model=DataResponse[EmployeeOut])
async def unlock(employee_id: int, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).unlock(actor, employee_id)}


@router.post("/{employee_id}/invite")
async def regenerate_invite(employee_id: int, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).regenerate_invite(actor, employee_id)}


@router.get("/{employee_id}/rates")
async def rates(employee_id: int, _: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).rates(employee_id)}


@router.post("/{employee_id}/rates")
async def add_rate(employee_id: int, body: RateBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    effective_date = body.effective_date or body.effective_from
    mode = body.mode
    if body.effective_from and body.mode == "next_shift":
        mode = "date"
    return {"data": await EmployeeService(session).add_rate(
        actor, employee_id, body.hourly_rate, mode, effective_date, body.reason, body.confirm_large_change,
    )}


@router.post("/{employee_id}/rates/{rate_id}/cancel")
async def cancel_rate(employee_id: int, rate_id: int, body: RateCancelBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).cancel_rate(actor, employee_id, rate_id, body.reason)}
