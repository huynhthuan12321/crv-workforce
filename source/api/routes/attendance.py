from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, TodayOut, WorkSessionOut
from source.services.rate_limit import attendance_rate_limiter
from source.services.workforce import AttendanceService, session_dict

router = APIRouter()


class LocationBody(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=10000)


@router.get("/today", response_model=DataResponse[TodayOut])
async def today(employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    return {"data": await AttendanceService(session).today(employee)}


@router.post("/check-in", response_model=DataResponse[WorkSessionOut])
async def check_in(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    await attendance_rate_limiter.check(employee.id, "check-in")
    row = await AttendanceService(session).check_in(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}


@router.post("/check-out", response_model=DataResponse[WorkSessionOut])
async def check_out(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    await attendance_rate_limiter.check(employee.id, "check-out")
    row = await AttendanceService(session).check_out(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}
