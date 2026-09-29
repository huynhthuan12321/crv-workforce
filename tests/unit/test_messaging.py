from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from source.database.models import (
    AnnouncementRecipientOrm,
    EmployeeLocationAssignmentOrm,
    EmployeeOrm,
    NotificationOutboxOrm,
    AnnouncementOrm,
    ConversationOrm,
    MessageOrm,
    MessageRelayOrm,
    PendingFreeMessageOrm,
    WorkLocationOrm,
)
from source.enums import EmployeeRole
from source.enums import OutboxStatus
from source.domain.workforce_errors import WorkforceError
from source.services.messaging import MessagingService
from source.utils.clock import FakeClock, VIETNAM_TZ
from datetime import datetime


NOW = datetime(2026, 9, 29, 10, 0, tzinfo=VIETNAM_TZ)


async def employee(session, code: str, role: EmployeeRole, telegram_id: int | None, active: bool = True):
    row = EmployeeOrm(code=code, full_name=code, role=role, telegram_id=telegram_id, is_active=active)
    session.add(row)
    await session.flush()
    return row


@pytest.mark.asyncio
async def test_2_21_announcement_never_leaks_employee_to_employee(session_factory):
    async with session_factory() as session, session.begin():
        director = await employee(session, "GD001", EmployeeRole.director, 9001)
        nv1 = await employee(session, "NV001", EmployeeRole.employee, 1001)
        nv2 = await employee(session, "NV002", EmployeeRole.employee, 1002)
        result = await MessagingService(session, FakeClock(NOW)).create_announcement(
            director, "Nội dung", "employees",
        )
        rows = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert result["recipient_count"] == 2
        assert {row.chat_id for row in rows} == {1001, 1002}
        assert 9001 not in {row.chat_id for row in rows}


@pytest.mark.asyncio
async def test_2_21_manager_audience_restricted_and_skips_unlinked_locked(session_factory):
    async with session_factory() as session, session.begin():
        manager = await employee(session, "QL001", EmployeeRole.manager, 9001)
        await employee(session, "NV001", EmployeeRole.employee, 1001)
        await employee(session, "NV002", EmployeeRole.employee, None)
        await employee(session, "NV003", EmployeeRole.employee, 1003, active=False)
        result = await MessagingService(session, FakeClock(NOW)).create_announcement(manager, "Tin", "all")
        assert result["recipient_count"] == 1
        assert result["skipped_count"] == 2


@pytest.mark.asyncio
async def test_2_21_acknowledge_idempotent(session_factory):
    async with session_factory() as session, session.begin():
        director = await employee(session, "GD001", EmployeeRole.director, 9001)
        recipient = await employee(session, "NV001", EmployeeRole.employee, 1001)
        await MessagingService(session, FakeClock(NOW)).create_announcement(director, "Tin", "custom", employee_ids=[recipient.id])
        row = await session.scalar(select(AnnouncementRecipientOrm))
        first = await MessagingService(session, FakeClock(NOW)).acknowledge(row.announcement_id, recipient)
        second = await MessagingService(session, FakeClock(NOW + timedelta(minutes=1))).acknowledge(row.announcement_id, recipient)
        assert first["acknowledged_at"] == second["acknowledged_at"]


@pytest.mark.asyncio
async def test_2_21_location_audience_only_sends_assigned_employees(session_factory):
    async with session_factory() as session, session.begin():
        director = await employee(session, "GD001", EmployeeRole.director, 9001)
        nv1 = await employee(session, "NV001", EmployeeRole.employee, 1001)
        nv2 = await employee(session, "NV002", EmployeeRole.employee, 1002)
        location = WorkLocationOrm(code="KHO01", name="Kho", latitude=10, longitude=106, radius_m=100, coordinate_source="manual_coordinates", is_active=True)
        session.add(location)
        await session.flush()
        session.add(EmployeeLocationAssignmentOrm(employee_id=nv1.id, location_id=location.id, effective_from=NOW))
        await session.flush()
        result = await MessagingService(session, FakeClock(NOW)).create_announcement(director, "Kho", "location", location_id=location.id)
        assert result["recipient_count"] == 1
        rows = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert [row.chat_id for row in rows] == [1001]


@pytest.mark.asyncio
async def test_2_21_text_limit_rejects_over_2000(session_factory):
    async with session_factory() as session, session.begin():
        director = await employee(session, "GD001", EmployeeRole.director, 9001)
        with pytest.raises(WorkforceError) as exc:
            await MessagingService(session).create_announcement(director, "x" * 2001, "employees")
        assert exc.value.code == "MESSAGE_TOO_LONG"


@pytest.mark.asyncio
async def test_2_21_reply_manager_announcement_reaches_manager_and_director(session_factory):
    async with session_factory() as session, session.begin():
        manager = await employee(session, "QL001", EmployeeRole.manager, 2001)
        director = await employee(session, "GD001", EmployeeRole.director, 3001)
        sender = await employee(session, "NV001", EmployeeRole.employee, 1001)
        created = await MessagingService(session, FakeClock(NOW)).create_announcement(
            manager, "Ca chiều đổi giờ", "custom", employee_ids=[sender.id],
        )
        announcement = await session.get(AnnouncementOrm, created["id"])
        await MessagingService(session, FakeClock(NOW)).send_message(
            sender, manager, "Em đã nhận.", "manager", announcement_id=announcement.id,
        )
        rows = list((await session.scalars(select(NotificationOutboxOrm).order_by(NotificationOutboxOrm.id))).all())
        assert {row.chat_id for row in rows[-2:]} == {2001, 3001}


@pytest.mark.asyncio
async def test_2_21_reply_director_announcement_only_reaches_director(session_factory):
    async with session_factory() as session, session.begin():
        director = await employee(session, "GD001", EmployeeRole.director, 3001)
        sender = await employee(session, "NV001", EmployeeRole.employee, 1001)
        created = await MessagingService(session, FakeClock(NOW)).create_announcement(
            director, "Thông báo", "custom", employee_ids=[sender.id],
        )
        await MessagingService(session, FakeClock(NOW)).send_message(
            sender, director, "Đã rõ.", "director", announcement_id=created["id"],
        )
        rows = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert [row.chat_id for row in rows[-1:]] == [3001]


def _bot_message(*, telegram_id: int, text: str, message_id: int = 50, reply_id: int | None = None):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=telegram_id),
        chat=SimpleNamespace(id=telegram_id),
        message_id=message_id,
        text=text,
        reply_to_message=SimpleNamespace(message_id=reply_id) if reply_id is not None else None,
        answer=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_2_21_free_message_choose_manager_via_real_handler(session_factory, monkeypatch):
    import source.telegram.handlers.user.callbacks as callbacks
    import source.telegram.handlers.user.messages as handlers
    async with session_factory() as session, session.begin():
        await employee(session, "NV001", EmployeeRole.employee, 1001)
        await employee(session, "QL001", EmployeeRole.manager, 2001)
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    monkeypatch.setattr(callbacks, "session_factory", session_factory)
    message = _bot_message(telegram_id=1001, text="xin nghỉ chiều")
    await handlers.echo(message)
    markup = message.answer.await_args.kwargs["reply_markup"]
    callback_data = markup.inline_keyboard[0][0].callback_data
    assert callback_data.startswith("free_target:manager:")
    assert callback_data.rsplit(":", 1)[1] != "None"
    callback = SimpleNamespace(
        data=callback_data,
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    await callbacks.free_target(callback)
    async with session_factory() as session:
        outbox = list((await session.scalars(select(NotificationOutboxOrm))).all())
        conversation = await session.scalar(select(ConversationOrm).where(ConversationOrm.channel == "manager"))
        assert [row.chat_id for row in outbox] == [2001]
        assert conversation is not None


@pytest.mark.asyncio
async def test_2_21_free_message_choose_director_and_manager_only_director(session_factory, monkeypatch):
    import source.telegram.handlers.user.callbacks as callbacks
    import source.telegram.handlers.user.messages as handlers
    async with session_factory() as session, session.begin():
        await employee(session, "NV001", EmployeeRole.employee, 1001)
        await employee(session, "QL001", EmployeeRole.manager, 2001)
        await employee(session, "GD001", EmployeeRole.director, 3001)
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    monkeypatch.setattr(callbacks, "session_factory", session_factory)
    for sender_id, target in ((1001, "manager"), (2001, "director")):
        message = _bot_message(telegram_id=sender_id, text="Cần trao đổi")
        await handlers.echo(message)
        markup = message.answer.await_args.kwargs["reply_markup"]
        callback_data = markup.inline_keyboard[0][0].callback_data
        assert f"free_target:{target}:" in callback_data
        callback = SimpleNamespace(
            data=callback_data,
            from_user=SimpleNamespace(id=sender_id),
            message=SimpleNamespace(edit_text=AsyncMock()),
            answer=AsyncMock(),
        )
        await callbacks.free_target(callback)
    async with session_factory() as session:
        rows = list((await session.scalars(select(NotificationOutboxOrm).order_by(NotificationOutboxOrm.id))).all())
        assert [row.chat_id for row in rows] == [2001, 3001]


@pytest.mark.asyncio
async def test_2_21_free_message_expired_after_10_min(session_factory, monkeypatch):
    import source.telegram.handlers.user.callbacks as callbacks
    import source.telegram.handlers.user.messages as handlers
    async with session_factory() as session, session.begin():
        await employee(session, "NV001", EmployeeRole.employee, 1001)
        await employee(session, "QL001", EmployeeRole.manager, 2001)
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    monkeypatch.setattr(callbacks, "session_factory", session_factory)
    message = _bot_message(telegram_id=1001, text="Hết hạn")
    await handlers.echo(message)
    callback_data = message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data
    async with session_factory() as session, session.begin():
        pending = await session.scalar(select(PendingFreeMessageOrm))
        pending.expires_at = NOW - timedelta(minutes=1)
    callback = SimpleNamespace(
        data=callback_data,
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    await callbacks.free_target(callback)
    callback.answer.assert_awaited_once()
    assert "hết hạn" in callback.answer.await_args.args[0]
    async with session_factory() as session:
        assert await session.scalar(select(NotificationOutboxOrm)) is None


@pytest.mark.asyncio
async def test_2_21_reply_forwarded_goes_only_to_original_sender(session_factory, monkeypatch):
    import source.telegram.handlers.user.messages as handlers
    async with session_factory() as session, session.begin():
        nv1 = await employee(session, "NV001", EmployeeRole.employee, 1001)
        nv2 = await employee(session, "NV002", EmployeeRole.employee, 1002)
        manager = await employee(session, "QL001", EmployeeRole.manager, 2001)
        original = (await MessagingService(session, FakeClock(NOW)).send_message(
            nv1, manager, "Xin nghỉ", "manager",
        ))[0]
        session.add(MessageRelayOrm(message_id=original.id, chat_id=2001, telegram_message_id=777))
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    message = _bot_message(telegram_id=2001, text="Đã nhận", reply_id=777)
    await handlers.echo(message)
    async with session_factory() as session:
        rows = list((await session.scalars(select(NotificationOutboxOrm))).all())
        private_rows = [row for row in rows if row.notification_type == "private_message"]
        assert private_rows[-1].chat_id == 1001
        assert private_rows[-1].payload["sender_code"] == "QL001"
        assert 1002 not in [row.chat_id for row in private_rows[-1:]]


@pytest.mark.asyncio
async def test_2_21_photo_rejected(session_factory, monkeypatch):
    import source.telegram.handlers.user.messages as handlers
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    message = SimpleNamespace(answer=AsyncMock())
    await handlers.unsupported_message(message)
    assert "chỉ hỗ trợ tin nhắn chữ" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_2_21_keyboard_buttons_not_captured_as_free_message(session_factory, monkeypatch):
    import source.telegram.handlers.user.messages as handlers
    async with session_factory() as session, session.begin():
        await employee(session, "QL001", EmployeeRole.manager, 2001)
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    message = _bot_message(telegram_id=2001, text="💰 Duyệt lương")
    await handlers.echo(message)
    async with session_factory() as session:
        assert await session.scalar(select(PendingFreeMessageOrm)) is None


@pytest.mark.asyncio
async def test_2_21_end_to_end_free_message_and_reply(session_factory, monkeypatch):
    import source.telegram.handlers.user.callbacks as callbacks
    import source.telegram.handlers.user.messages as handlers
    from source.workers import process_notifications

    async with session_factory() as session, session.begin():
        await employee(session, "NV001", EmployeeRole.employee, 1001)
        await employee(session, "QL001", EmployeeRole.manager, 2001)
    monkeypatch.setattr(handlers, "session_factory", session_factory)
    monkeypatch.setattr(callbacks, "session_factory", session_factory)

    employee_message = _bot_message(telegram_id=1001, text="xin nghỉ chiều", message_id=901)
    await handlers.echo(employee_message)
    callback_data = employee_message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data
    callback = SimpleNamespace(
        data=callback_data,
        from_user=SimpleNamespace(id=1001),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    await callbacks.free_target(callback)

    class Bot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append((chat_id, text))
            return SimpleNamespace(message_id=500 + len(self.sent))

    bot = Bot()
    await process_notifications(bot, session_factory, FakeClock(NOW))
    assert bot.sent[0][0] == 2001
    assert "NV001" in bot.sent[0][1]
    assert "xin nghỉ chiều" in bot.sent[0][1]

    manager_message_id = bot.sent[0][1] and 501
    manager_reply = _bot_message(telegram_id=2001, text="Đã nhận", reply_id=manager_message_id)
    await handlers.echo(manager_reply)
    async with session_factory() as session:
        rows = list((await session.scalars(select(NotificationOutboxOrm).order_by(NotificationOutboxOrm.id))).all())
        assert rows[-1].chat_id == 1001
        assert rows[-1].status == OutboxStatus.pending
