from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_or_director
from source.database.models import EmployeeOrm
from source.services.workforce import ReviewService, session_dict

router = APIRouter()


class CloseBody(BaseModel):
    check_out_time: datetime
    reason: str = Field(min_length=5, max_length=200)


class EditBody(BaseModel):
    check_in_time: datetime
    check_out_time: datetime
    reason: str = Field(min_length=5, max_length=200)


@router.get("/pending")
async def pending(_: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await ReviewService(session).pending()}


@router.get("/resolved")
async def resolved(_: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await ReviewService(session).list_resolved()}


@router.post("/{session_id}/flags-reviewed")
async def mark(session_id: int, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await ReviewService(session).mark_flags(actor, session_id)
    return {"data": session_dict(row)}


@router.post("/{session_id}/close")
async def close(session_id: int, body: CloseBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await ReviewService(session).close_forgotten(actor, session_id, body.check_out_time, body.reason)
    return {"data": session_dict(row)}


@router.patch("/{session_id}")
async def edit(session_id: int, body: EditBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await ReviewService(session).edit_session(actor, session_id, body.check_in_time, body.check_out_time, body.reason)
    return {"data": session_dict(row)}
