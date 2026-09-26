from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm, PayBatchOrm, WorkSessionOrm
from source.services.workforce import session_dict

router = APIRouter()


@router.get("")
async def history(from_: date | None = None, to: date | None = None,
                  employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    query = select(WorkSessionOrm).where(WorkSessionOrm.employee_id == employee.id)
    if from_:
        query = query.where(WorkSessionOrm.work_date >= from_)
    if to:
        query = query.where(WorkSessionOrm.work_date <= to)
    rows = (await session.scalars(query.order_by(WorkSessionOrm.work_date.desc(), WorkSessionOrm.check_in_at))).all()
    batches = (await session.scalars(select(PayBatchOrm).where(PayBatchOrm.employee_id == employee.id).order_by(PayBatchOrm.work_date.desc(), PayBatchOrm.batch_no))).all()
    return {"data": {"sessions": [session_dict(x) for x in rows],
            "batches": [{"id": x.id, "date": x.work_date, "batch_no": x.batch_no, "amount": x.amount} for x in batches]}}
