from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import require_roles
from source.database.models import EmployeeOrm
from source.enums import EmployeeRole
from source.schemas.workforce import DataResponse, ProductTotalOut, ReportSummaryOut, ReportTimeseriesOut
from source.services.workforce import ReportService

router = APIRouter()
director_only = require_roles(EmployeeRole.director)


@router.get("/summary", response_model=DataResponse[ReportSummaryOut])
async def summary(period: str = Query(pattern="^(day|week|month)$"), date_: date = Query(alias="date"),
                  employee_id: int | None = None, _: EmployeeOrm = Depends(director_only),
                  session: AsyncSession = Depends(get_session)):
    return {"data": await ReportService(session).summary(period, date_, employee_id)}


@router.get("/products", response_model=DataResponse[list[ProductTotalOut]])
async def products(period: str = Query(pattern="^(day|week|month)$"), date_: date = Query(alias="date"),
                   employee_id: int | None = None, _: EmployeeOrm = Depends(director_only),
                   session: AsyncSession = Depends(get_session)):
    return {"data": await ReportService(session).products(period, date_, employee_id)}


@router.get("/timeseries", response_model=DataResponse[list[ReportTimeseriesOut]])
async def timeseries(period: str = Query(pattern="^(day|week|month)$"), date_: date = Query(alias="date"),
                     employee_id: int | None = None, _: EmployeeOrm = Depends(director_only),
                     session: AsyncSession = Depends(get_session)):
    return {"data": await ReportService(session).timeseries(period, date_, employee_id)}
