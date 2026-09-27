from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_only
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, EmployeeOut
from source.services.workforce import EmployeeService

router = APIRouter()


class EmployeeBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=2, max_length=200)
    hourly_rate: int = Field(gt=0)
    effective_from: date


class RateBody(BaseModel):
    hourly_rate: int = Field(gt=0)
    effective_from: date


@router.get("", response_model=DataResponse[list[EmployeeOut]])
async def employees(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    active: bool | None = Query(default=None),
    _: EmployeeOrm = Depends(manager_only),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await EmployeeService(session).list(q=q, active=active)}


@router.post("")
async def add(body: EmployeeBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await EmployeeService(session).create(actor, body.code, body.full_name, body.hourly_rate, body.effective_from)}


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
    return {"data": await EmployeeService(session).add_rate(actor, employee_id, body.hourly_rate, body.effective_from)}
