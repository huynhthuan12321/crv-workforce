from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from source.database.models import (
    AnnouncementOrm,
    AnnouncementRecipientOrm,
    ConversationOrm,
    EmployeeLocationAssignmentOrm,
    EmployeeOrm,
    MessageOrm,
    MessageRelayOrm,
    NotificationOutboxOrm,
    PendingFreeMessageOrm,
    WorkLocationOrm,
)
from source.domain.workforce_errors import fail
from source.enums import EmployeeRole, OutboxStatus
from source.services.workforce import current_location_assignment
from source.utils.clock import Clock, VIETNAM_TZ


MAX_MESSAGE_LENGTH = 2000
CHANNEL_MANAGER = "manager"
CHANNEL_DIRECTOR = "director"


def _now(clock: Clock | None = None) -> datetime:
    return (clock or Clock()).now()


def _as_vn(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=VIETNAM_TZ)
    return value.astimezone(VIETNAM_TZ)


def _channel_for_role(role: EmployeeRole) -> str:
    return CHANNEL_DIRECTOR if role == EmployeeRole.director else CHANNEL_MANAGER


async def _current_employee_ids(session: AsyncSession, *, role: EmployeeRole | None = None,
                                location_id: int | None = None,
                                employee_ids: list[int] | None = None) -> list[EmployeeOrm]:
    query = select(EmployeeOrm).where(
        EmployeeOrm.role == (role or EmployeeRole.employee),
    )
    if employee_ids:
        query = query.where(EmployeeOrm.id.in_(employee_ids))
    if location_id:
        query = query.where(EmployeeOrm.id.in_(select(EmployeeLocationAssignmentOrm.employee_id).where(
            EmployeeLocationAssignmentOrm.location_id == location_id,
            EmployeeLocationAssignmentOrm.effective_to.is_(None),
        )))
    return list((await session.scalars(query.order_by(EmployeeOrm.code))).all())


class MessagingService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session = session
        self.clock = clock or Clock()

    async def announcement_recipients(self, actor: EmployeeOrm, audience_type: str,
                                      location_id: int | None = None,
                                      employee_ids: list[int] | None = None) -> tuple[list[EmployeeOrm], int]:
        if audience_type not in {"all", "managers", "employees", "location", "custom"}:
            raise fail("ANNOUNCEMENT_AUDIENCE_INVALID", 422)
        if actor.role == EmployeeRole.manager and audience_type not in {"all", "location", "custom", "employees"}:
            raise fail("FORBIDDEN", 403)
        if actor.role == EmployeeRole.manager:
            target_role = EmployeeRole.employee
        elif audience_type == "managers":
            target_role = EmployeeRole.manager
        elif audience_type in {"employees", "location", "custom", "all"}:
            target_role = EmployeeRole.employee
        else:
            target_role = None
        if audience_type == "all" and actor.role == EmployeeRole.director:
            candidates = list((await self.session.scalars(select(EmployeeOrm).where(
                EmployeeOrm.role.in_([EmployeeRole.manager, EmployeeRole.employee]),
            ))).all())
        else:
            candidates = await _current_employee_ids(
                self.session,
                role=target_role,
                location_id=location_id if audience_type == "location" else None,
                employee_ids=employee_ids if audience_type == "custom" else None,
            )
        recipients = [row for row in candidates if row.is_active and row.telegram_id]
        skipped = len(candidates) - len(recipients)
        return recipients, skipped

    async def create_announcement(self, actor: EmployeeOrm, body: str, audience_type: str,
                                  location_id: int | None = None,
                                  employee_ids: list[int] | None = None) -> dict:
        body = body.strip()
        if not body or len(body) > MAX_MESSAGE_LENGTH:
            raise fail("MESSAGE_TOO_LONG" if len(body) > MAX_MESSAGE_LENGTH else "MESSAGE_EMPTY", 422)
        recipients, skipped = await self.announcement_recipients(
            actor, audience_type, location_id, employee_ids,
        )
        announcement = AnnouncementOrm(
            sender_id=actor.id,
            sender_role=actor.role.value,
            audience_type=audience_type,
            location_id=location_id,
            body=body,
        )
        self.session.add(announcement)
        await self.session.flush()
        now = _now(self.clock)
        for employee in recipients:
            recipient = AnnouncementRecipientOrm(
                announcement_id=announcement.id,
                employee_id=employee.id,
            )
            self.session.add(recipient)
            await self.session.flush()
            self.session.add(NotificationOutboxOrm(
                dedupe_key=f"announcement:{announcement.id}:{employee.id}",
                chat_id=employee.telegram_id,
                notification_type="announcement",
                payload={
                    "announcement_id": announcement.id,
                    "recipient_id": recipient.id,
                    "sender_role": actor.role.value,
                    "sender_name": actor.full_name,
                    "body": body,
                },
            ))
        return {
            "id": announcement.id,
            "body": body,
            "audience_type": audience_type,
            "recipient_count": len(recipients),
            "skipped_count": skipped,
            "created_at": now.isoformat(),
        }

    async def acknowledge(self, announcement_id: int, employee: EmployeeOrm) -> dict:
        recipient = await self.session.scalar(select(AnnouncementRecipientOrm).where(
            AnnouncementRecipientOrm.announcement_id == announcement_id,
            AnnouncementRecipientOrm.employee_id == employee.id,
        ).with_for_update())
        if not recipient:
            raise fail("NOT_FOUND", 404)
        if recipient.acknowledged_at is None:
            recipient.acknowledged_at = _now(self.clock)
        return {"acknowledged_at": recipient.acknowledged_at.isoformat()}

    async def _conversation(self, employee_id: int, channel: str) -> ConversationOrm:
        row = await self.session.scalar(select(ConversationOrm).where(
            ConversationOrm.employee_id == employee_id,
            ConversationOrm.channel == channel,
        ))
        if row:
            return row
        row = ConversationOrm(employee_id=employee_id, channel=channel)
        self.session.add(row)
        await self.session.flush()
        return row

    async def send_message(self, sender: EmployeeOrm, recipient: EmployeeOrm, body: str,
                           channel: str, announcement_id: int | None = None) -> list[MessageOrm]:
        body = body.strip()
        if not body or len(body) > MAX_MESSAGE_LENGTH:
            raise fail("MESSAGE_TOO_LONG" if len(body) > MAX_MESSAGE_LENGTH else "MESSAGE_EMPTY", 422)
        if not recipient.is_active or not recipient.telegram_id:
            raise fail("RECIPIENT_UNAVAILABLE", 422)
        # A conversation is keyed by the non-staff participant for the channel:
        # employee ↔ manager lives under the employee; manager/employee ↔ director
        # lives under the person contacting the director. This keeps inbox rows
        # meaningful regardless of message direction.
        if channel == CHANNEL_DIRECTOR:
            participant_id = recipient.id if sender.role == EmployeeRole.director else sender.id
        else:
            participant_id = sender.id if sender.role == EmployeeRole.employee else recipient.id
        conversation = await self._conversation(participant_id, channel)
        message = MessageOrm(
            conversation_id=conversation.id,
            sender_id=sender.id,
            direction="from_staff" if sender.role == EmployeeRole.employee else "to_staff",
            body=body,
            announcement_id=announcement_id,
        )
        self.session.add(message)
        await self.session.flush()
        targets = [recipient]
        if sender.role == EmployeeRole.employee and announcement_id:
            announcement = await self.session.get(AnnouncementOrm, announcement_id)
            if announcement and announcement.sender_id != sender.id:
                original_sender = await self.session.get(EmployeeOrm, announcement.sender_id)
                if original_sender and original_sender.telegram_id:
                    targets = [original_sender]
                    if original_sender.role == EmployeeRole.manager:
                        targets += list((await self.session.scalars(select(EmployeeOrm).where(
                            EmployeeOrm.role == EmployeeRole.director,
                            EmployeeOrm.is_active.is_(True),
                            EmployeeOrm.telegram_id.is_not(None),
                        ))).all())
        for target in targets:
            self.session.add(NotificationOutboxOrm(
                dedupe_key=f"message:{message.id}:{target.id}",
                chat_id=target.telegram_id,
                notification_type="private_message",
                payload={
                    "message_id": message.id,
                    "sender_id": sender.id,
                    "sender_code": sender.code,
                    "sender_name": sender.full_name,
                    "sender_role": sender.role.value,
                    "body": body,
                },
            ))
        return [message]

    async def create_pending_free_message(
        self,
        sender: EmployeeOrm,
        body: str,
        telegram_message_id: int,
    ) -> PendingFreeMessageOrm:
        body = body.strip()
        if not body or len(body) > MAX_MESSAGE_LENGTH:
            raise fail("MESSAGE_TOO_LONG" if len(body) > MAX_MESSAGE_LENGTH else "MESSAGE_EMPTY", 422)
        pending = PendingFreeMessageOrm(
            employee_id=sender.id,
            text=body,
            telegram_message_id=telegram_message_id,
            expires_at=_now(self.clock) + timedelta(minutes=10),
        )
        self.session.add(pending)
        await self.session.flush()
        return pending

    async def send_pending_free_message(
        self,
        sender: EmployeeOrm,
        pending_id: int,
        target_role: EmployeeRole,
    ) -> int:
        pending = await self.session.get(PendingFreeMessageOrm, pending_id, with_for_update=True)
        if not pending or pending.employee_id != sender.id:
            raise fail("FREE_MESSAGE_EXPIRED", 422)
        if _as_vn(pending.expires_at) < _now(self.clock):
            await self.session.delete(pending)
            raise fail("FREE_MESSAGE_EXPIRED", 422)
        if target_role not in {EmployeeRole.manager, EmployeeRole.director}:
            raise fail("RECIPIENT_UNAVAILABLE", 422)
        if sender.role == EmployeeRole.manager:
            target_role = EmployeeRole.director
        recipients = list((await self.session.scalars(select(EmployeeOrm).where(
            EmployeeOrm.role == target_role,
            EmployeeOrm.is_active.is_(True),
            EmployeeOrm.telegram_id.is_not(None),
        ))).all())
        if not recipients:
            raise fail("RECIPIENT_UNAVAILABLE", 422)
        channel = CHANNEL_DIRECTOR if target_role == EmployeeRole.director else CHANNEL_MANAGER
        for recipient in recipients:
            await self.send_message(sender, recipient, pending.text, channel)
        await self.session.delete(pending)
        return len(recipients)

    async def list_conversations(self, viewer: EmployeeOrm, channel: str) -> list[dict]:
        if viewer.role == EmployeeRole.employee:
            raise fail("FORBIDDEN", 403)
        if channel not in {CHANNEL_MANAGER, CHANNEL_DIRECTOR}:
            raise fail("CHANNEL_INVALID", 422)
        if viewer.role == EmployeeRole.manager and channel != CHANNEL_MANAGER:
            raise fail("FORBIDDEN", 403)
        query = select(ConversationOrm, EmployeeOrm).join(EmployeeOrm, EmployeeOrm.id == ConversationOrm.employee_id).where(
            ConversationOrm.channel == channel,
        )
        rows = list((await self.session.execute(query.order_by(ConversationOrm.id.desc()))).all())
        result = []
        for conversation, employee in rows:
            result.append({
                "id": conversation.id,
                "employee_id": employee.id,
                "employee_code": employee.code,
                "employee_name": employee.full_name,
                "channel": channel,
            })
        return result

    async def conversation_messages(self, viewer: EmployeeOrm, conversation_id: int) -> list[dict]:
        if viewer.role == EmployeeRole.employee:
            raise fail("FORBIDDEN", 403)
        conversation = await self.session.get(ConversationOrm, conversation_id)
        if not conversation:
            raise fail("NOT_FOUND", 404)
        if viewer.role == EmployeeRole.manager and conversation.channel != CHANNEL_MANAGER:
            raise fail("FORBIDDEN", 403)
        rows = list((await self.session.scalars(select(MessageOrm).where(
            MessageOrm.conversation_id == conversation_id,
        ).order_by(MessageOrm.created_at, MessageOrm.id))).all())
        return [{
            "id": row.id,
            "sender_id": row.sender_id,
            "direction": row.direction,
            "body": row.body,
            "announcement_id": row.announcement_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in rows]
