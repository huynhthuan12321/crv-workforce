from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_or_director
from source.database.models import EmployeeOrm
from source.services.workforce import PayrollService

router = APIRouter()


class ApproveBody(BaseModel):
    date: date
    employee_ids: list[int]


@router.get("")
async def list_payroll(date: date, _: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await PayrollService(session).list_payroll(date)}


@router.get("/{employee_id}")
async def detail(employee_id: int, date: date, _: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await PayrollService(session).get_employee_payroll_detail(employee_id, date)}


@router.post("/approve")
async def approve(body: ApproveBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        batches = await PayrollService(session).approve(actor, body.employee_ids, body.date)
    return {"data": [{
        "employee_id": batch.employee_id,
        "batch_id": batch.id,
        "batch_no": batch.batch_no,
        "amount": batch.amount,
    } for batch in batches]}
