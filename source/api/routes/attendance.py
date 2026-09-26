from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm
from source.services.workforce import AttendanceService, session_dict

router = APIRouter()


class LocationBody(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=10000)


@router.get("/today")
async def today(employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    return {"data": await AttendanceService(session).today(employee)}


@router.post("/check-in")
async def check_in(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    row = await AttendanceService(session).check_in(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}


@router.post("/check-out")
async def check_out(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    row = await AttendanceService(session).check_out(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}
