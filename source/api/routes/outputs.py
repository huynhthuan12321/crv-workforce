from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm
from source.services.workforce import OutputService

router = APIRouter()


class OutputBody(BaseModel):
    items: dict[str, int]


@router.get("/{session_id}")
async def form(session_id: int, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    return {"data": await OutputService(session).form(employee, session_id)}


@router.put("/{session_id}")
async def submit(session_id: int, body: OutputBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    result = await OutputService(session).submit(employee, session_id, body.items)
    return {"data": result}
