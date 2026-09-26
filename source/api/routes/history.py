from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, HistoryOut
from source.services.workforce import HistoryService

router = APIRouter()


@router.get("", response_model=DataResponse[HistoryOut])
async def history(from_: date | None = None, to: date | None = None,
                  employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    return {"data": await HistoryService(session).history(employee, from_, to)}
