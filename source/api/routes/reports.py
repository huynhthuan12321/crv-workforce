from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import require_roles
from source.database.models import EmployeeOrm, OutputItemOrm, OutputLogOrm, ProductOrm, WorkSessionOrm
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import ceil_money

router = APIRouter()
director_only = require_roles(EmployeeRole.director)


def bounds(period: str, day: date) -> tuple[date, date]:
    if period == "day": return day, day
    if period == "week":
        start = day - timedelta(days=day.weekday()); return start, start + timedelta(days=6)
    start = day.replace(day=1)
    following = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, following - timedelta(days=1)


@router.get("/summary")
async def summary(period: str = Query(pattern="^(day|week|month)$"), date_: date = Query(alias="date"),
                  employee_id: int | None = None, _: EmployeeOrm = Depends(director_only),
                  session: AsyncSession = Depends(get_session)):
    start, end = bounds(period, date_)
    filters = [WorkSessionOrm.work_date.between(start, end), WorkSessionOrm.status == SessionStatus.closed]
    if employee_id: filters.append(WorkSessionOrm.employee_id == employee_id)
    minutes, raw = (await session.execute(select(func.coalesce(func.sum(WorkSessionOrm.minutes), 0),
        func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(*filters))).one()
    production = (await session.execute(select(func.coalesce(func.sum(OutputItemOrm.bags), 0),
        func.coalesce(func.sum(OutputItemOrm.kg), 0)).join(OutputLogOrm).join(WorkSessionOrm)
        .where(*filters))).one()
    return {"data": {"from": start, "to": end, "minutes": int(minutes),
            "salary": ceil_money(raw) if raw else 0, "bags": int(production[0]), "kg": float(production[1])}}


@router.get("/products")
async def products(period: str = Query(pattern="^(day|week|month)$"), date_: date = Query(alias="date"),
                   _: EmployeeOrm = Depends(director_only), session: AsyncSession = Depends(get_session)):
    start, end = bounds(period, date_)
    rows = (await session.execute(select(ProductOrm.code, ProductOrm.name,
        func.coalesce(func.sum(OutputItemOrm.bags), 0), func.coalesce(func.sum(OutputItemOrm.kg), 0))
        .join(OutputItemOrm, OutputItemOrm.product_id == ProductOrm.id)
        .join(OutputLogOrm, OutputLogOrm.id == OutputItemOrm.output_log_id)
        .join(WorkSessionOrm, WorkSessionOrm.id == OutputLogOrm.work_session_id)
        .where(WorkSessionOrm.work_date.between(start, end)).group_by(ProductOrm.id))).all()
    return {"data": [{"code": x[0], "name": x[1], "bags": int(x[2]), "kg": float(x[3])} for x in rows]}
