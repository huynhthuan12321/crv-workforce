from datetime import timedelta

import pytest
from sqlalchemy import select

from source.database.models import (
    AnnouncementRecipientOrm,
    EmployeeLocationAssignmentOrm,
    EmployeeOrm,
    NotificationOutboxOrm,
    AnnouncementOrm,
    WorkLocationOrm,
)
from source.enums import EmployeeRole
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
