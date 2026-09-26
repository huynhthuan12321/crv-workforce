from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import employee_only
from source.database.models import EmployeeOrm, LocationConsentOrm
from source.domain.workforce_errors import fail
from source.services.workforce import ConsentService, current_consent
from source.utils.clock import Clock

router = APIRouter()


class ConsentBody(BaseModel):
    version: int


@router.get("/current")
async def get_current(employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    text, accepted = await current_consent(session, employee.id, Clock().now())
    return {"data": None if not text else {"version": text.version, "content": text.content,
            "effective_at": text.effective_at, "accepted": accepted}}


@router.post("")
async def accept(body: ConsentBody, employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    now = Clock().now()
    text, _ = await current_consent(session, employee.id, now)
    if not text or body.version != text.version:
        raise fail("CONSENT_VERSION_INVALID", 422)
    session.add(LocationConsentOrm(employee_id=employee.id, consent_version=body.version, consented_at=now))
    return {"data": {"accepted": True, "version": body.version}}


@router.post("/withdraw")
async def withdraw(employee: EmployeeOrm = Depends(employee_only), session: AsyncSession = Depends(get_session)):
    await ConsentService(session).withdraw(employee)
    return {"data": {"accepted": False}}
