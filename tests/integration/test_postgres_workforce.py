import os
import asyncio
from datetime import date, datetime
from decimal import Decimal

import pytest
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
    PayBatchOrm,
    RateHistoryOrm,
    ProductOrm,
    SyncOutboxOrm,
    WorkLocationOrm,
    WorkSessionOrm,
)
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import AttendanceService, PayrollService, ReportService, ReviewService, WorkLocationService
from source.utils.clock import FakeClock, VIETNAM_TZ


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
    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=date(2026, 4, 1)))
    text_row = ConsentTextOrm(version=1, content="consent", effective_at=dt(6))
    session.add(text_row)
    await session.flush()
    session.add(LocationConsentOrm(employee_id=employee.id, consent_version=1, consented_at=dt(6)))
    await session.flush()


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
