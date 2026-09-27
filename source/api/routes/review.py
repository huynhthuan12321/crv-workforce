from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_or_director
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import WorkforceError
from source.schemas.workforce import DataResponse, ReviewResolvedOut, ReviewSessionOut, WorkSessionOut
from source.services.workforce import ReviewService, session_dict
from source.utils.clock import to_vn

router = APIRouter()


class CloseBody(BaseModel):
    check_out_time: datetime
    reason: str

    @field_validator("check_out_time")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        try:
            return to_vn(value)
        except WorkforceError as exc:
            raise ValueError(exc.code) from exc


class EditBody(BaseModel):
    check_in_time: datetime
    check_out_time: datetime
    reason: str

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        try:
            return to_vn(value)
        except WorkforceError as exc:
            raise ValueError(exc.code) from exc


@router.get("/pending", response_model=DataResponse[list[ReviewSessionOut]])
async def pending(
    type: str | None = Query(default=None, pattern="^(gps|forgot)$"),
    _: EmployeeOrm = Depends(manager_or_director),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await ReviewService(session).pending(type)}


@router.get("/resolved", response_model=DataResponse[list[ReviewResolvedOut]])
async def resolved(
    type: str | None = Query(default=None, pattern="^(gps|forgot)$"),
    _: EmployeeOrm = Depends(manager_or_director),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await ReviewService(session).list_resolved(type)}


@router.post("/{session_id}/flags-reviewed", response_model=DataResponse[WorkSessionOut])
async def mark(session_id: int, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    row = await ReviewService(session).mark_flags(actor, session_id)
    return {"data": session_dict(row)}


@router.post("/{session_id}/close", response_model=DataResponse[WorkSessionOut])
async def close(session_id: int, body: CloseBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    row = await ReviewService(session).close_forgotten(actor, session_id, body.check_out_time, body.reason)
    return {"data": session_dict(row)}


@router.patch("/{session_id}", response_model=DataResponse[WorkSessionOut])
async def edit(session_id: int, body: EditBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    row = await ReviewService(session).edit_session(actor, session_id, body.check_in_time, body.check_out_time, body.reason)
    return {"data": session_dict(row)}
