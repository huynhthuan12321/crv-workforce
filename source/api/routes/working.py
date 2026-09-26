from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_only
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, WorkingNowOut
from source.services.workforce import WorkingService

router = APIRouter()


@router.get("", response_model=DataResponse[list[WorkingNowOut]])
async def working_now(_: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkingService(session).working_now()}
