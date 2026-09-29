import os
import asyncio
import subprocess
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy import func, select, update
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from source.bot_main import acquire_bot_lock
from source.database.models import (
    Base,
    ConsentTextOrm,
    EmployeeLocationAssignmentOrm,
    EmployeeOrm,
    LocationConsentOrm,
    NotificationOutboxOrm,
    PayBatchOrm,
    RateHistoryOrm,
    ProductOrm,
    SyncOutboxOrm,
    WorkLocationOrm,
    WorkSessionOrm,
)
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import AttendanceService, EmployeeService, PayrollService, ReportService, ReviewService, WorkLocationService, rate_row_at
from source.utils.clock import FakeClock, VIETNAM_TZ
from source.workers import notification_text


pytestmark = pytest.mark.postgres


def dt(hour: int, minute: int = 0):
    return datetime(2026, 4, 24, hour, minute, tzinfo=VIETNAM_TZ)


def real_phone_dt(hour: int, minute: int = 0):
    return datetime(2026, 9, 27, hour, minute, tzinfo=VIETNAM_TZ)


@pytest.fixture()
async def pg_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        if os.getenv("CRV_REQUIRE_POSTGRES") == "1":
            pytest.fail("CRV_REQUIRE_POSTGRES=1 but TEST_DATABASE_URL is not set")
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_async_engine(url, pool_pre_ping=True, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def make_employee(session, code="NV001", role=EmployeeRole.employee):
    location = await session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.code == "KHO01"))
    if not location:
        location = WorkLocationOrm(
            code="KHO01",
            name="Kho 01",
            latitude=Decimal("10.0000000"),
            longitude=Decimal("106.0000000"),
            radius_m=100,
            coordinate_source="manual_coordinates",
            is_active=True,
        )
        session.add(location)
        await session.flush()
    row = EmployeeOrm(code=code, full_name=code, role=role, is_active=True)
    session.add(row)
    await session.flush()
    if role == EmployeeRole.employee:
        current = await session.scalar(
            select(EmployeeLocationAssignmentOrm).where(
                EmployeeLocationAssignmentOrm.employee_id == row.id,
                EmployeeLocationAssignmentOrm.effective_to.is_(None),
            )
        )
        if not current:
            session.add(EmployeeLocationAssignmentOrm(
                employee_id=row.id,
                location_id=location.id,
                effective_from=dt(6),
                reason="default test assignment",
            ))
            await session.flush()
    return row


async def make_location(session, code="KHO01", name="Kho 01", lat=Decimal("10.0000000"), lng=Decimal("106.0000000"), radius=100, active=True):
    row = WorkLocationOrm(
        code=code,
        name=name,
        latitude=lat,
        longitude=lng,
        radius_m=radius,
        coordinate_source="manual_coordinates",
        is_active=active,
    )
    session.add(row)
    await session.flush()
    return row


async def assign_location(session, employee_id: int, location_id: int, effective_from=None, effective_to=None):
    row = EmployeeLocationAssignmentOrm(
        employee_id=employee_id,
        location_id=location_id,
        effective_from=effective_from or dt(6),
        effective_to=effective_to,
        reason="test assignment",
    )
    session.add(row)
    await session.flush()
    return row


def session_row(employee_id: int, status=SessionStatus.open, check_in=None, check_out=None):
    check_in = check_in or dt(8)
    minutes = int((check_out - check_in).total_seconds() // 60) if check_out else None
    return WorkSessionOrm(
        employee_id=employee_id,
        work_date=check_in.date(),
        check_in_at=check_in,
        check_out_at=check_out,
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        work_location_id=1,
        location_code_snapshot="KHO01",
        location_name_snapshot="Kho 01",
        location_lat_snapshot=Decimal("10.0000000"),
        location_lng_snapshot=Decimal("106.0000000"),
        location_radius_m_snapshot=100,
        rate_snapshot=30_000,
        minutes=minutes,
        amount_raw=(Decimal(minutes) * Decimal(30_000) / Decimal(60)) if minutes else None,
        status=status,
        flags=[],
    )


async def test_partial_unique_open_index(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            employee = await make_employee(session)
            session.add(session_row(employee.id, SessionStatus.open))
    async with pg_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(session_row(employee.id, SessionStatus.open, check_in=dt(9)))
    async with pg_factory() as session:
        async with session.begin():
            session.add(session_row(employee.id, SessionStatus.closed, check_in=dt(9), check_out=dt(10)))


async def test_concurrent_payroll_approve_one(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            session.add(session_row(employee.id, SessionStatus.closed, check_in=dt(8), check_out=dt(9)))
            manager_id, employee_id = manager.id, employee.id

    async def approve_once():
        async with pg_factory() as session:
            try:
                async with session.begin():
                    actor = await session.get(EmployeeOrm, manager_id)
                    return await PayrollService(session).approve_one(actor, employee_id, date(2026, 4, 24))
            except WorkforceError as exc:
                return exc.code

    results = await asyncio.gather(approve_once(), approve_once())
    assert sum(isinstance(item, PayBatchOrm) for item in results) == 1
    assert results.count("NO_ELIGIBLE_SESSIONS") == 1

    async with pg_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PayBatchOrm)) == 1


async def test_concurrent_close_forgotten(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            row = session_row(employee.id, SessionStatus.needs_review, check_in=dt(8))
            row.review_reason = "forgot_checkout"
            session.add(row)
            await session.flush()
            manager_id, session_id = manager.id, row.id

    async def close_once():
        async with pg_factory() as session:
            try:
                async with session.begin():
                    actor = await session.get(EmployeeOrm, manager_id)
                    return await ReviewService(session, FakeClock(dt(20))).close_forgotten(
                        actor, session_id, dt(17), "quên bấm ra ca"
                    )
            except WorkforceError as exc:
                return exc.code

    results = await asyncio.gather(close_once(), close_once())
    assert sum(isinstance(item, WorkSessionOrm) for item in results) == 1
    assert results.count("ALREADY_HANDLED") == 1


async def test_forgotten_close_rejects_future_and_overlap_on_postgres(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            first = session_row(employee.id, SessionStatus.needs_review, check_in=real_phone_dt(9, 59))
            first.review_reason = "forgot_checkout"
            second = session_row(employee.id, SessionStatus.needs_review, check_in=real_phone_dt(17, 49))
            second.review_reason = "forgot_checkout"
            open_row = session_row(employee.id, SessionStatus.open, check_in=real_phone_dt(19, 21))
            session.add_all([first, second, open_row])
            await session.flush()
            manager_id, first_id, second_id = manager.id, first.id, second.id

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            service = ReviewService(session, FakeClock(real_phone_dt(19, 24)))
            with pytest.raises(WorkforceError) as exc:
                await service.close_forgotten(actor, first_id, real_phone_dt(20, 0), "quên bấm ra ca")
            assert exc.value.code == "CHECKOUT_IN_FUTURE"
            assert exc.value.status_code == 422
            assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            service = ReviewService(session, FakeClock(real_phone_dt(19, 24)))
            with pytest.raises(WorkforceError) as exc:
                await service.close_forgotten(actor, first_id, real_phone_dt(18, 0), "quên bấm ra ca")
            assert exc.value.code == "SESSION_OVERLAP"
            assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"

            bounds = await service.checkout_bounds(second_id)
            assert bounds["max_check_out"] == "2026-09-27T19:21:00+07:00"

            with pytest.raises(WorkforceError) as exc:
                await service.close_forgotten(actor, second_id, real_phone_dt(19, 22), "quên bấm ra ca")
            assert exc.value.code == "SESSION_OVERLAP"
            assert exc.value.details["max_check_out"] == "2026-09-27T19:21:00+07:00"
            assert exc.value.details["overlap"]["check_out_at"] is None


async def test_edit_session_rejects_future_and_overlap_on_postgres(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            editable = session_row(employee.id, SessionStatus.closed, check_in=real_phone_dt(9, 59), check_out=real_phone_dt(10, 10))
            next_row = session_row(employee.id, SessionStatus.needs_review, check_in=real_phone_dt(17, 49))
            next_row.review_reason = "forgot_checkout"
            session.add_all([editable, next_row])
            await session.flush()
            manager_id, editable_id = manager.id, editable.id

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            service = ReviewService(session, FakeClock(real_phone_dt(19, 24)))
            with pytest.raises(WorkforceError) as exc:
                await service.edit_session(actor, editable_id, real_phone_dt(9, 59), real_phone_dt(20, 0), "sửa theo sổ giấy")
            assert exc.value.code == "CHECKOUT_IN_FUTURE"
            assert exc.value.status_code == 422

            with pytest.raises(WorkforceError) as exc:
                await service.edit_session(actor, editable_id, real_phone_dt(9, 59), real_phone_dt(18, 0), "sửa theo sổ giấy")
            assert exc.value.code == "SESSION_OVERLAP"
            assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"


async def test_bot_advisory_lock_autocommit_idle(pg_factory):
    engine = pg_factory.kw["bind"]
    lock1 = await acquire_bot_lock(engine)
    assert lock1 is not None
    try:
        pid = await lock1.scalar(text("SELECT pg_backend_pid()"))
        lock2 = await acquire_bot_lock(engine)
        assert lock2 is None
        async with pg_factory() as session:
            state = await session.scalar(text("SELECT state FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid})
            assert state == "idle"
    finally:
        await lock1.scalar(text("SELECT pg_advisory_unlock(910202601)"))
        await lock1.close()


async def add_rate_and_consent(session, employee: EmployeeOrm):
    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=dt(0), reason="test rate"))
    text_row = await session.get(ConsentTextOrm, 1)
    if not text_row:
        text_row = ConsentTextOrm(version=1, content="consent", effective_at=dt(6))
        session.add(text_row)
        await session.flush()
    session.add(LocationConsentOrm(employee_id=employee.id, consent_version=1, consented_at=dt(6)))
    await session.flush()


async def test_2_18_s3_checkin_uses_rate_at_timestamp_and_snapshot_is_immutable(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            opened = await AttendanceService(session, FakeClock(dt(8))).check_in(employee, 10, 106, 10)
            assert opened.rate_snapshot == 30_000

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            changed = await EmployeeService(session, FakeClock(dt(9))).add_rate(
                manager, employee_id, 40_000, mode="next_shift", reason="Tăng theo năng lực",
            )
            assert changed["hourly_rate"] == 40_000

    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            closed = await AttendanceService(session, FakeClock(dt(10))).check_out(employee, 10, 106, 10)
            assert closed.rate_snapshot == 30_000
            assert int(closed.amount_raw) == 60_000

    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            opened = await AttendanceService(session, FakeClock(dt(11))).check_in(employee, 10, 106, 10)
            assert opened.rate_snapshot == 40_000

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            preview = await EmployeeService(session, FakeClock(dt(12))).add_rate(
                manager, employee_id, 15_000, mode="next_shift", reason="Điều chỉnh nhiệm vụ",
            )
            assert preview["requires_confirmation"] is True
            changed = await EmployeeService(session, FakeClock(dt(12))).add_rate(
                manager, employee_id, 15_000, mode="next_shift", reason="Điều chỉnh nhiệm vụ", confirm_large_change=True,
            )
            assert changed["hourly_rate"] == 15_000

    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            closed = await AttendanceService(session, FakeClock(dt(13))).check_out(employee, 10, 106, 10)
            assert closed.rate_snapshot == 40_000


async def test_2_18_s3_edit_and_close_forgotten_do_not_change_rate_snapshot(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            row = session_row(employee.id, SessionStatus.needs_review, check_in=dt(8))
            row.rate_snapshot = 30_000
            row.review_reason = "forgot_checkout"
            session.add(row)
            await session.flush()
            manager_id, employee_id, session_id = manager.id, employee.id, row.id

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            await EmployeeService(session, FakeClock(dt(9))).add_rate(
                manager, employee_id, 40_000, mode="next_shift", reason="Tăng theo năng lực",
            )
            closed = await ReviewService(session, FakeClock(dt(10))).close_forgotten(manager, session_id, dt(9), "bổ sung giờ ra")
            assert closed.rate_snapshot == 30_000

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            edited = await ReviewService(session, FakeClock(dt(11))).edit_session(manager, session_id, dt(8), dt(9, 30), "sửa theo sổ")
            assert edited.rate_snapshot == 30_000


async def test_2_18_s4_multiple_rates_one_day_round_once_with_locations(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            kho2 = await make_location(session, "KHO02", "Kho 02", lng=Decimal("106.0100000"))
            session.add(session_row(employee.id, SessionStatus.closed, check_in=dt(8), check_out=dt(10)))
            row2 = session_row(employee.id, SessionStatus.closed, check_in=dt(13), check_out=dt(17))
            row2.rate_snapshot = 40_000
            row2.amount_raw = Decimal(240) * Decimal(40_000) / Decimal(60)
            row2.work_location_id = kho2.id
            row2.location_code_snapshot = kho2.code
            row2.location_name_snapshot = kho2.name
            session.add(row2)
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            summary = (await PayrollService(session).list_payroll(date(2026, 4, 24)))[0]
            assert summary["rate_snapshots"] == [30_000, 40_000]
            assert summary["day_total_rounded"] == 220_000
            manager = await session.get(EmployeeOrm, manager_id)
            batch = await PayrollService(session).approve_one(manager, employee_id, date(2026, 4, 24))
            assert batch.amount == 220_000


async def test_2_18_s2_schedule_cancel_pending_and_rate_bounds(pg_factory, monkeypatch):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=datetime(2026, 10, 1, 0, 0, tzinfo=VIETNAM_TZ), reason="test rate"))
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            scheduled = await EmployeeService(session, FakeClock(datetime(2026, 10, 31, 10, 0, tzinfo=VIETNAM_TZ))).add_rate(
                manager, employee_id, 40_000, mode="date", effective_date=date(2026, 11, 1), reason="Thay đổi công việc",
            )
            assert scheduled["is_pending"] is True
            before = await rate_row_at(session, employee_id, datetime(2026, 10, 31, 23, 0, tzinfo=VIETNAM_TZ))
            after = await rate_row_at(session, employee_id, datetime(2026, 11, 1, 0, 5, tzinfo=VIETNAM_TZ))
            assert before.hourly_rate == 30_000
            assert after.hourly_rate == 40_000

            with pytest.raises(WorkforceError) as exc:
                await EmployeeService(session, FakeClock(datetime(2026, 10, 31, 10, 5, tzinfo=VIETNAM_TZ))).add_rate(
                    manager, employee_id, 45_000, mode="date", effective_date=date(2026, 11, 2), reason="Thay đổi công việc",
                )
            assert exc.value.code == "RATE_PENDING_EXISTS"

            cancelled = await EmployeeService(session, FakeClock(datetime(2026, 10, 31, 10, 10, tzinfo=VIETNAM_TZ))).cancel_rate(
                manager, employee_id, scheduled["id"], "Hủy theo yêu cầu",
            )
            assert cancelled["is_cancelled"] is True
            after_cancel = await rate_row_at(session, employee_id, datetime(2026, 11, 1, 0, 5, tzinfo=VIETNAM_TZ))
            assert after_cancel.hourly_rate == 30_000

            rescheduled = await EmployeeService(session, FakeClock(datetime(2026, 10, 31, 10, 15, tzinfo=VIETNAM_TZ))).add_rate(
                manager, employee_id, 45_000, mode="date", effective_date=date(2026, 11, 2), reason="Thay đổi công việc",
            )
            assert rescheduled["hourly_rate"] == 45_000

            with pytest.raises(WorkforceError) as exc:
                await EmployeeService(session, FakeClock(datetime(2026, 11, 3, 10, 0, tzinfo=VIETNAM_TZ))).cancel_rate(
                    manager, employee_id, rescheduled["id"], "Hủy theo yêu cầu",
                )
            assert exc.value.code == "RATE_ALREADY_EFFECTIVE"

            with pytest.raises(WorkforceError) as exc:
                await EmployeeService(session, FakeClock(datetime(2026, 10, 31, 10, 20, tzinfo=VIETNAM_TZ))).add_rate(
                    manager, employee_id, 999, mode="next_shift", reason="Điều chỉnh tạm thời",
                )
            assert exc.value.code == "RATE_OUT_OF_RANGE"


async def test_2_18_s2_immediate_change_keeps_future_pending(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=datetime(2026, 10, 1, 0, 0, tzinfo=VIETNAM_TZ), reason="test rate"))
            session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=40_000, effective_from=datetime(2026, 11, 1, 0, 0, tzinfo=VIETNAM_TZ), reason="pending rate"))
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            immediate = await EmployeeService(session, FakeClock(datetime(2026, 10, 20, 9, 0, tzinfo=VIETNAM_TZ))).add_rate(
                manager, employee_id, 35_000, mode="next_shift", reason="Điều chỉnh nhiệm vụ",
            )
            assert immediate["hourly_rate"] == 35_000
            today = await rate_row_at(session, employee_id, datetime(2026, 10, 20, 9, 1, tzinfo=VIETNAM_TZ))
            future = await rate_row_at(session, employee_id, datetime(2026, 11, 1, 0, 5, tzinfo=VIETNAM_TZ))
            assert today.hourly_rate == 35_000
            assert future.hourly_rate == 40_000


async def test_2_18_s6_rate_change_notifications_dedupe_and_text(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            employee.telegram_id = 1001
            session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=dt(0), reason="test rate"))
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            changed = await EmployeeService(session, FakeClock(dt(9))).add_rate(manager, employee_id, 40_000, mode="next_shift", reason="Tăng theo năng lực")
            scheduled = await EmployeeService(session, FakeClock(dt(9, 5))).add_rate(manager, employee_id, 45_000, mode="date", effective_date=date(2026, 4, 25), reason="Thay đổi công việc")
            cancelled = await EmployeeService(session, FakeClock(dt(9, 10))).cancel_rate(manager, employee_id, scheduled["id"], "Hủy theo yêu cầu")
            assert changed["id"] and cancelled["is_cancelled"]

    async with pg_factory() as session:
        rows = (await session.scalars(select(NotificationOutboxOrm).order_by(NotificationOutboxOrm.dedupe_key))).all()
        keys = [row.dedupe_key for row in rows]
        assert len(keys) == len(set(keys))
        texts = [notification_text(row) for row in rows]
        assert any("Đơn giá của bạn đã được cập nhật" in text for text in texts)
        assert any("Đơn giá của bạn sẽ được cập nhật" in text for text in texts)
        assert any("đã được hủy" in text for text in texts)
        assert all("Tăng theo năng lực" not in text and "Thay đổi công việc" not in text for text in texts)


async def test_2_17_s2_assignments_history_unique_overlap_and_inactive_blocked(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            kho2 = await make_location(session, "KHO02", "Kho 02", lng=Decimal("106.0100000"))
            inactive = await make_location(session, "KHO03", "Kho 03", lng=Decimal("106.0200000"), active=False)
            employee_id, manager_id, kho2_id, inactive_id = employee.id, manager.id, kho2.id, inactive.id

    async with pg_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(EmployeeLocationAssignmentOrm(employee_id=employee_id, location_id=kho2_id, effective_from=dt(7)))

    async with pg_factory() as session:
        async with session.begin():
            await session.execute(update(EmployeeLocationAssignmentOrm).where(
                EmployeeLocationAssignmentOrm.employee_id == employee_id,
                EmployeeLocationAssignmentOrm.effective_to.is_(None),
            ).values(effective_to=dt(7)))
            session.add(EmployeeLocationAssignmentOrm(employee_id=employee_id, location_id=1, effective_from=dt(8), effective_to=dt(12)))
            await session.flush()
            with pytest.raises(IntegrityError):
                session.add(EmployeeLocationAssignmentOrm(employee_id=employee_id, location_id=kho2_id, effective_from=dt(11), effective_to=dt(13)))
                await session.flush()

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            with pytest.raises(WorkforceError) as exc:
                await WorkLocationService(session).assign_employee(actor, employee_id, inactive_id, "chuyển kho test")
            assert exc.value.code == "LOCATION_INACTIVE"


async def test_2_17_s3_r10_assignment_change_during_open_uses_session_snapshot_and_nearby(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            kho2 = await make_location(session, "KHO02", "Kho 02", lat=Decimal("10.0004000"), lng=Decimal("106.0000000"), radius=100)
            ids = manager.id, employee.id, kho2.id

    manager_id, employee_id, kho2_id = ids
    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            open_row = await AttendanceService(session, FakeClock(dt(8))).check_in(employee, 10.0, 106.0, 10)
            assert open_row.location_code_snapshot == "KHO01"
            assert open_row.nearby_location_id == kho2_id

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            await WorkLocationService(session, FakeClock(dt(8, 30))).assign_employee(actor, employee_id, kho2_id, "chuyển sang kho 2")

    async with pg_factory() as session:
        async with session.begin():
            employee = await session.get(EmployeeOrm, employee_id)
            closed = await AttendanceService(session, FakeClock(dt(9))).check_out(employee, 10.0, 106.0, 10)
            assert closed.location_code_snapshot == "KHO01"
            second = await AttendanceService(session, FakeClock(dt(10))).check_in(employee, 10.0004, 106.0, 10)
            assert second.location_code_snapshot == "KHO02"


async def test_2_17_s1_3_location_changes_do_not_mutate_session_snapshot(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            row = await AttendanceService(session, FakeClock(dt(8))).check_in(employee, 10.0, 106.0, 10)
            session_id, manager_id = row.id, manager.id

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            await WorkLocationService(session).update(actor, 1, name="Kho đã đổi tên", latitude=10.2, longitude=106.2, radius_m=200, coordinate_source="manual_coordinates")
            row = await session.get(WorkSessionOrm, session_id)
            assert row.location_name_snapshot == "Kho 01"
            assert row.location_lat_snapshot == Decimal("10.0000000")
            assert row.location_radius_m_snapshot == 100


async def test_2_17_s4_deactivate_blocks_current_assignment_and_open_but_allows_history_and_needs_review(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            manager_id, employee_id = manager.id, employee.id

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            with pytest.raises(WorkforceError) as exc:
                await WorkLocationService(session).set_active(actor, 1, False)
            assert exc.value.code == "LOCATION_IN_USE"

    async with pg_factory() as session:
        async with session.begin():
            await session.execute(update(EmployeeLocationAssignmentOrm).where(EmployeeLocationAssignmentOrm.employee_id == employee_id).values(effective_to=dt(7)))
            session.add(session_row(employee_id, SessionStatus.open, check_in=dt(8)))

    async with pg_factory() as session:
        async with session.begin():
            actor = await session.get(EmployeeOrm, manager_id)
            with pytest.raises(WorkforceError) as exc:
                await WorkLocationService(session).set_active(actor, 1, False)
            assert exc.value.details["open_sessions"] == 1

    async with pg_factory() as session:
        async with session.begin():
            row = await session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.employee_id == employee_id))
            row.status = SessionStatus.needs_review
            row.review_reason = "forgot_checkout"
            actor = await session.get(EmployeeOrm, manager_id)
            result = await WorkLocationService(session).set_active(actor, 1, False)
            assert result["is_active"] is False


async def test_2_17_s6_payroll_filters_location_without_changing_rounding_unit_and_report_uses_raw_by_location(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await make_employee(session, "QL001", EmployeeRole.manager)
            employee = await make_employee(session)
            kho2 = await make_location(session, "KHO02", "Kho 02", lng=Decimal("106.0100000"))
            a = session_row(employee.id, SessionStatus.closed, check_in=dt(8), check_out=dt(11, 13))
            a.amount_raw = Decimal("96500")
            a.minutes = 193
            b = session_row(employee.id, SessionStatus.closed, check_in=dt(13), check_out=dt(15, 10))
            b.work_location_id = kho2.id
            b.location_code_snapshot = "KHO02"
            b.location_name_snapshot = "Kho 02"
            b.location_lng_snapshot = Decimal("106.0100000")
            b.amount_raw = Decimal("65000")
            b.minutes = 130
            session.add_all([a, b])
            await session.flush()
            manager_id, employee_id, kho1_id, kho2_id = manager.id, employee.id, 1, kho2.id

    async with pg_factory() as session:
        async with session.begin():
            payroll_a = await PayrollService(session).list_payroll(date(2026, 4, 24), location_id=kho1_id)
            row = next(item for item in payroll_a if item["employee_id"] == employee_id)
            assert row["pending_amount"] == 162_000
            actor = await session.get(EmployeeOrm, manager_id)
            batch = await PayrollService(session).approve_one(actor, employee_id, date(2026, 4, 24))
            assert batch.amount == 162_000
            summary_a = await ReportService(session).summary("day", date(2026, 4, 24), location_id=kho1_id)
            summary_b = await ReportService(session).summary("day", date(2026, 4, 24), location_id=kho2_id)
            assert row["day_locations"] == [
                {"id": kho1_id, "code": "KHO01", "name": "Kho 01"},
                {"id": kho2_id, "code": "KHO02", "name": "Kho 02"},
            ]
            assert summary_a["salary"]["total"] == 96_500
            assert summary_b["salary"]["total"] == 65_000


async def test_2_17_s8_check_in_does_not_need_workshop_env(pg_factory, monkeypatch):
    monkeypatch.delenv("WORKSHOP__LAT", raising=False)
    monkeypatch.delenv("WORKSHOP__LNG", raising=False)
    monkeypatch.delenv("WORKSHOP__RADIUS_M", raising=False)
    async with pg_factory() as session:
        async with session.begin():
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            row = await AttendanceService(session, FakeClock(dt(8))).check_in(employee, 10.0, 106.0, 10)
            assert row.location_code_snapshot == "KHO01"


async def test_2_17_s10_outbox_event_keeps_event_id_and_schema_version(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            employee = await make_employee(session)
            await add_rate_and_consent(session, employee)
            await AttendanceService(session, FakeClock(dt(8))).check_in(employee, 10.0, 106.0, 10)
            await AttendanceService(session, FakeClock(dt(9))).check_out(employee, 10.0, 106.0, 10)
            row = await session.scalar(select(SyncOutboxOrm).where(SyncOutboxOrm.event_type == "session_closed"))
            event_id = row.payload["event_id"]
            row.attempts += 1
            await session.flush()
            same = await session.get(SyncOutboxOrm, row.id)
            assert same.payload["schema_version"] == 2
            assert same.payload["event_id"] == event_id
            assert same.payload["session"]["location"]["code"] == "KHO01"


async def _assert_no_open_session_on_inactive_location(factory):
    async with factory() as session:
        rows = (await session.execute(text("""
            SELECT ws.id
            FROM work_sessions ws
            JOIN work_locations wl ON wl.id = ws.work_location_id
            WHERE ws.status = 'open' AND wl.is_active = false
        """))).all()
        assert rows == []


async def test_2_17_s5_assign_vs_checkin(pg_factory):
    for idx in range(5):
        async with pg_factory() as session:
            async with session.begin():
                manager = await make_employee(session, f"QLA{idx}", EmployeeRole.manager)
                employee = await make_employee(session, f"NVA{idx}")
                await add_rate_and_consent(session, employee)
                kho2 = await make_location(session, f"KB{idx}", f"Kho B {idx}", lng=Decimal("106.0100000"))
                manager_id, employee_id, kho2_id = manager.id, employee.id, kho2.id

        async def checkin_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        employee = await session.get(EmployeeOrm, employee_id)
                        return await AttendanceService(session, FakeClock(dt(8, idx))).check_in(employee, 10.0, 106.0, 10)
                except WorkforceError as exc:
                    return exc.code

        async def assign_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        actor = await session.get(EmployeeOrm, manager_id)
                        return await WorkLocationService(session, FakeClock(dt(8, idx))).assign_employee(actor, employee_id, kho2_id, "race đổi kho")
                except WorkforceError as exc:
                    return exc.code

        results = await asyncio.gather(checkin_once(), assign_once())
        assert not any(item == "LOCATION_INACTIVE" for item in results)
        async with pg_factory() as session:
            row = await session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.employee_id == employee_id))
            assert row is not None
            assert row.work_location_id in {1, kho2_id}
            if row.work_location_id == 1:
                assert (row.location_code_snapshot, row.location_name_snapshot) == ("KHO01", "Kho 01")
            else:
                assert (row.location_code_snapshot, row.location_name_snapshot) == (f"KB{idx}", f"Kho B {idx}")


async def test_2_17_s5_deactivate_vs_checkin(pg_factory):
    for idx in range(5):
        async with pg_factory() as session:
            async with session.begin():
                manager = await make_employee(session, f"QLD{idx}", EmployeeRole.manager)
                employee = await make_employee(session, f"NVD{idx}")
                await add_rate_and_consent(session, employee)
                manager_id, employee_id = manager.id, employee.id

        async def checkin_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        employee = await session.get(EmployeeOrm, employee_id)
                        return await AttendanceService(session, FakeClock(dt(8, idx))).check_in(employee, 10.0, 106.0, 10)
                except WorkforceError as exc:
                    return exc.code

        async def deactivate_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        actor = await session.get(EmployeeOrm, manager_id)
                        return await WorkLocationService(session).set_active(actor, 1, False)
                except WorkforceError as exc:
                    return exc.code

        results = await asyncio.gather(checkin_once(), deactivate_once())
        assert any(item in {"LOCATION_IN_USE", "LOCATION_INACTIVE"} or isinstance(item, WorkSessionOrm) for item in results)
        await _assert_no_open_session_on_inactive_location(pg_factory)


async def test_2_17_s5_deactivate_vs_assign(pg_factory):
    for idx in range(5):
        async with pg_factory() as session:
            async with session.begin():
                manager = await make_employee(session, f"QLX{idx}", EmployeeRole.manager)
                employee = await make_employee(session, f"NVX{idx}")
                target = await make_location(session, f"KX{idx}", f"Kho X {idx}", lng=Decimal("106.0200000"))
                manager_id, employee_id, target_id = manager.id, employee.id, target.id

        async def assign_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        actor = await session.get(EmployeeOrm, manager_id)
                        return await WorkLocationService(session, FakeClock(dt(8, idx))).assign_employee(actor, employee_id, target_id, "race phân công")
                except WorkforceError as exc:
                    return exc.code

        async def deactivate_once():
            async with pg_factory() as session:
                try:
                    async with session.begin():
                        actor = await session.get(EmployeeOrm, manager_id)
                        return await WorkLocationService(session).set_active(actor, target_id, False)
                except WorkforceError as exc:
                    return exc.code

        await asyncio.gather(deactivate_once(), assign_once())
        async with pg_factory() as session:
            bad = await session.scalar(select(func.count()).select_from(EmployeeLocationAssignmentOrm)
                .join(WorkLocationOrm, WorkLocationOrm.id == EmployeeLocationAssignmentOrm.location_id)
                .where(EmployeeLocationAssignmentOrm.effective_to.is_(None), WorkLocationOrm.is_active.is_(False)))
            assert bad == 0


def _run_alembic_for_db(db_url, database: str, revision: str) -> None:
    env = os.environ.copy()
    env["APP__ENV"] = "development"
    env["TG__BOT_TOKEN"] = env.get("TG__BOT_TOKEN", "test")
    env["DB__HOST"] = db_url.host or "localhost"
    env["DB__PORT"] = str(db_url.port or 5432)
    env["DB__USER"] = db_url.username or "default"
    env["DB__PASSWORD"] = db_url.password or "password"
    env["DB__NAME"] = database
    env["WORKSHOP__LAT"] = "10.0"
    env["WORKSHOP__LNG"] = "106.0"
    env["WORKSHOP__RADIUS_M"] = "100"
    subprocess.run(["alembic", "upgrade", revision], check=True, env=env, cwd=os.getcwd(), capture_output=True, text=True)


async def test_2_17_s9_migration_on_data_copy():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        if os.getenv("CRV_REQUIRE_POSTGRES") == "1":
            pytest.fail("CRV_REQUIRE_POSTGRES=1 but TEST_DATABASE_URL is not set")
        pytest.skip("TEST_DATABASE_URL is not set")
    db_url = make_url(url)
    db_name = f"crv_mig_217_{uuid.uuid4().hex[:10]}"
    admin_engine = create_async_engine(db_url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        _run_alembic_for_db(db_url, db_name, "0003")
        target_engine = create_async_engine(db_url.set(database=db_name), poolclass=NullPool)
        try:
            async with target_engine.begin() as conn:
                await conn.execute(text("INSERT INTO employees (code, full_name, role, is_active) VALUES ('NVOLD', 'NV Old', 'employee', true), ('QLOLD', 'QL Old', 'manager', true)"))
                await conn.execute(text("INSERT INTO products (code, name, kg_per_bag, sort_order) VALUES ('BOT', 'Bột', 1.2, 1)"))
                employee_id = await conn.scalar(text("SELECT id FROM employees WHERE code='NVOLD'"))
                manager_id = await conn.scalar(text("SELECT id FROM employees WHERE code='QLOLD'"))
                batch_id = await conn.scalar(text("""
                    INSERT INTO pay_batches (employee_id, work_date, batch_no, amount, day_total_rounded_at_approval, status, approved_by)
                    VALUES (:employee_id, '2026-04-24', 1, 30000, 30000, 'paid', :manager_id)
                    RETURNING id
                """), {"employee_id": employee_id, "manager_id": manager_id})
                session_id = await conn.scalar(text("""
                    INSERT INTO work_sessions (
                        employee_id, work_date, check_in_at, check_out_at,
                        check_in_lat, check_in_lng, check_in_accuracy_m, check_in_distance_m,
                        check_out_lat, check_out_lng, check_out_accuracy_m, check_out_distance_m,
                        rate_snapshot, minutes, amount_raw, status, flags, pay_batch_id, version
                    ) VALUES
                    (:employee_id, '2026-04-24', '2026-04-24 08:00:00+07', '2026-04-24 09:00:00+07',
                     10.0, 106.0, 10, 0, 10.002, 106.0, 10, 222, 30000, 60, 30000, 'closed', '["gps_out_of_range"]'::jsonb, :batch_id, 1)
                    RETURNING id
                """), {"employee_id": employee_id, "batch_id": batch_id})
                output_id = await conn.scalar(text("INSERT INTO output_logs (work_session_id, submitted_at, locked_at) VALUES (:session_id, now(), now()) RETURNING id"), {"session_id": session_id})
                product_id = await conn.scalar(text("SELECT id FROM products WHERE code='BOT'"))
                await conn.execute(text("INSERT INTO output_items (output_log_id, product_id, bags, kg) VALUES (:output_id, :product_id, 2, 2.4)"), {"output_id": output_id, "product_id": product_id})
            async with target_engine.connect() as conn:
                before = await conn.scalar(text("SELECT count(*) FROM work_sessions"))
            _run_alembic_for_db(db_url, db_name, "head")
            async with target_engine.connect() as conn:
                after = await conn.scalar(text("SELECT count(*) FROM work_sessions"))
                missing = await conn.scalar(text("SELECT count(*) FROM work_sessions WHERE work_location_id IS NULL OR location_code_snapshot IS NULL OR location_radius_m_snapshot IS NULL"))
                flag_source = await conn.scalar(text("SELECT flag_source FROM work_sessions LIMIT 1"))
                output_count = await conn.scalar(text("SELECT count(*) FROM output_items"))
                batch_count = await conn.scalar(text("SELECT count(*) FROM pay_batches"))
            assert before == after == 1
            assert missing == 0
            assert flag_source == "check_out"
            assert output_count == 1
            assert batch_count == 1
            subprocess.run(["alembic", "downgrade", "0003"], check=True, env={
                **os.environ,
                "APP__ENV": "development", "TG__BOT_TOKEN": "test",
                "DB__HOST": db_url.host or "localhost", "DB__PORT": str(db_url.port or 5432),
                "DB__USER": db_url.username or "default", "DB__PASSWORD": db_url.password or "password",
                "DB__NAME": db_name,
            }, cwd=os.getcwd(), capture_output=True, text=True)
            _run_alembic_for_db(db_url, db_name, "head")
        finally:
            await target_engine.dispose()
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        await admin_engine.dispose()
