from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import get_current_employee, manager_or_director
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import fail
from source.enums import EmployeeRole
from source.services.messaging import MessagingService

router = APIRouter()


class AnnouncementBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    audience_type: Literal["all", "managers", "employees", "location", "custom"]
    location_id: int | None = None
    employee_ids: list[int] = Field(default_factory=list)


class MessageBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    announcement_id: int | None = None


@router.post("/announcements")
async def create_announcement(
    body: AnnouncementBody,
    actor: EmployeeOrm = Depends(manager_or_director),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await MessagingService(session).create_announcement(
        actor, body.body, body.audience_type, body.location_id, body.employee_ids,
    )}


@router.get("/announcements")
async def list_announcements(
    actor: EmployeeOrm = Depends(get_current_employee),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import func, select
    from source.database.models import AnnouncementOrm, AnnouncementRecipientOrm
    query = select(AnnouncementOrm).order_by(AnnouncementOrm.created_at.desc())
    if actor.role == EmployeeRole.manager:
        query = query.outerjoin(
            AnnouncementRecipientOrm,
            AnnouncementRecipientOrm.announcement_id == AnnouncementOrm.id,
        ).where(
            (AnnouncementOrm.sender_id == actor.id)
            | (AnnouncementRecipientOrm.employee_id == actor.id)
        ).distinct()
    if actor.role == EmployeeRole.employee:
        query = query.join(AnnouncementRecipientOrm, AnnouncementRecipientOrm.announcement_id == AnnouncementOrm.id).where(
            AnnouncementRecipientOrm.employee_id == actor.id,
        )
    rows = list((await session.scalars(query)).all())
    result = []
    for row in rows:
        recipient_count = await session.scalar(
            select(func.count(AnnouncementRecipientOrm.id)).where(
                AnnouncementRecipientOrm.announcement_id == row.id,
            )
        )
        acknowledged_count = await session.scalar(
            select(func.count(AnnouncementRecipientOrm.id)).where(
                AnnouncementRecipientOrm.announcement_id == row.id,
                AnnouncementRecipientOrm.acknowledged_at.is_not(None),
            )
        )
        result.append({
            "id": row.id,
            "sender_id": row.sender_id,
            "sender_role": row.sender_role,
            "audience_type": row.audience_type,
            "location_id": row.location_id,
            "body": row.body,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "recipient_count": int(recipient_count or 0),
            "acknowledged_count": int(acknowledged_count or 0),
        })
    return {"data": result}


@router.post("/announcements/{announcement_id}/ack")
async def acknowledge(
    announcement_id: int,
    actor: EmployeeOrm = Depends(get_current_employee),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await MessagingService(session).acknowledge(announcement_id, actor)}


@router.get("/conversations")
async def conversations(
    channel: Literal["manager", "director"] = Query("manager"),
    actor: EmployeeOrm = Depends(get_current_employee),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await MessagingService(session).list_conversations(actor, channel)}


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(
    conversation_id: int,
    actor: EmployeeOrm = Depends(get_current_employee),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await MessagingService(session).conversation_messages(actor, conversation_id)}


@router.post("/conversations/{conversation_id}/messages")
async def send_conversation_message(
    conversation_id: int,
    body: MessageBody,
    actor: EmployeeOrm = Depends(get_current_employee),
    session: AsyncSession = Depends(get_session),
):
    if actor.role == EmployeeRole.employee:
        raise fail("FORBIDDEN", 403)
    from sqlalchemy import select
    from source.database.models import ConversationOrm, EmployeeOrm as E
    conversation = await session.scalar(select(ConversationOrm).where(ConversationOrm.id == conversation_id))
    if not conversation:
        raise fail("NOT_FOUND", 404)
    if actor.role == EmployeeRole.manager and conversation.channel != "manager":
        raise fail("FORBIDDEN", 403)
    if actor.role == EmployeeRole.director and conversation.channel != "director":
        raise fail("FORBIDDEN", 403)
    recipient = await session.get(E, conversation.employee_id)
    if actor.role == EmployeeRole.employee:
        managers = list((await session.scalars(select(E).where(
            E.role == EmployeeRole.manager, E.is_active.is_(True), E.telegram_id.is_not(None),
        ))).all())
        if not managers:
            raise fail("RECIPIENT_UNAVAILABLE", 422)
        targets = managers[:1]
    else:
        targets = [recipient]
    messages = []
    for target in targets:
        messages.extend(await MessagingService(session).send_message(
            actor, target, body.body, conversation.channel, body.announcement_id,
        ))
    return {"data": [{"id": row.id, "body": row.body} for row in messages]}
