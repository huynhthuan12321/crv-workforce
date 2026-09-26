from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from time import monotonic

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.config import settings
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import fail
from source.schemas.workforce import DataResponse, TodayOut, WorkSessionOut
from source.services.workforce import AttendanceService, session_dict

router = APIRouter()
_memory_limiter: dict[tuple[int, str], float] = {}


class LocationBody(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=10000)


async def _check_too_fast(employee_id: int, action: str) -> None:
    key = f"rl:attendance:{employee_id}:{action}"
    try:
        redis = settings.redis.redis_connection()
        try:
            ok = await redis.set(key, "1", ex=3, nx=True)
        finally:
            await redis.aclose()
        if not ok:
            raise fail("TOO_FAST", 429)
        return
    except Exception as exc:
        if getattr(exc, "code", None) == "TOO_FAST":
            raise
    now = monotonic()
    mem_key = (employee_id, action)
    previous = _memory_limiter.get(mem_key, 0)
    if now - previous < 3:
        raise fail("TOO_FAST", 429)
    _memory_limiter[mem_key] = now


@router.get("/today", response_model=DataResponse[TodayOut])
async def today(employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    return {"data": await AttendanceService(session).today(employee)}


@router.post("/check-in", response_model=DataResponse[WorkSessionOut])
async def check_in(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    await _check_too_fast(employee.id, "check-in")
    row = await AttendanceService(session).check_in(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}


@router.post("/check-out", response_model=DataResponse[WorkSessionOut])
async def check_out(body: LocationBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    await _check_too_fast(employee.id, "check-out")
    row = await AttendanceService(session).check_out(employee, body.lat, body.lng, body.accuracy_m)
    return {"data": session_dict(row)}
