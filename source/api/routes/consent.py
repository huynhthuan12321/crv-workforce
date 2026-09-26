from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import get_current_employee
from source.database.models import EmployeeOrm, LocationConsentOrm, NotificationOutboxOrm
from source.enums import EmployeeRole
from source.domain.workforce_errors import fail
from source.services.workforce import current_consent
from source.utils.clock import Clock

router = APIRouter()


class ConsentBody(BaseModel):
    version: int


@router.get("/current")
async def get_current(employee: EmployeeOrm = Depends(get_current_employee), session: AsyncSession = Depends(get_session)):
    text, accepted = await current_consent(session, employee.id, Clock().now())
    return {"data": None if not text else {"version": text.version, "content": text.content,
            "effective_at": text.effective_at, "accepted": accepted}}


@router.post("")
async def accept(body: ConsentBody, employee: EmployeeOrm = Depends(get_current_employee), session: AsyncSession = Depends(get_session)):
    now = Clock().now()
    text, _ = await current_consent(session, employee.id, now)
    if not text or body.version != text.version:
        raise fail("CONSENT_VERSION_INVALID", 422)
    async with session.begin():
        session.add(LocationConsentOrm(employee_id=employee.id, consent_version=body.version, consented_at=now))
    return {"data": {"accepted": True, "version": body.version}}


@router.post("/withdraw")
async def withdraw(employee: EmployeeOrm = Depends(get_current_employee), session: AsyncSession = Depends(get_session)):
    now = Clock().now()
    async with session.begin():
        text, accepted = await current_consent(session, employee.id, now)
        if text and accepted:
            row = await session.scalar(select(LocationConsentOrm).where(
                LocationConsentOrm.employee_id == employee.id,
                LocationConsentOrm.consent_version == text.version,
                LocationConsentOrm.withdrawn_at.is_(None)).order_by(LocationConsentOrm.id.desc()).limit(1))
            row.withdrawn_at = now
        managers = (await session.scalars(select(EmployeeOrm).where(
            EmployeeOrm.role == EmployeeRole.manager, EmployeeOrm.is_active.is_(True),
            EmployeeOrm.telegram_id.is_not(None)))).all()
        for manager in managers:
            session.add(NotificationOutboxOrm(
                dedupe_key=f"consent-withdrawn:{employee.id}:{int(now.timestamp())}",
                chat_id=manager.telegram_id, notification_type="consent_withdrawn",
                payload={"employee_id": employee.id, "employee_name": employee.full_name}))
    return {"data": {"accepted": False}}
