import os
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from source.database.models import Base, EmployeeLocationAssignmentOrm, EmployeeOrm, WorkLocationOrm, WorkSessionOrm
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import PayrollService, ReportService, ReviewService
from source.utils.clock import FakeClock, VIETNAM_TZ


pytestmark = pytest.mark.postgres


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


def dt(hour: int, minute: int = 0):
    return datetime(2026, 4, 24, hour, minute, tzinfo=VIETNAM_TZ)


def closed_session(employee_id: int, raw: int, flags: list[str] | None = None) -> WorkSessionOrm:
    minutes = raw // 500
    return WorkSessionOrm(
        employee_id=employee_id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(8),
        check_out_at=dt(8, minutes % 60),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        check_out_lat=Decimal("10"),
        check_out_lng=Decimal("106"),
        check_out_accuracy_m=Decimal("10"),
        check_out_distance_m=Decimal("0"),
        work_location_id=1,
        location_code_snapshot="KHO01",
        location_name_snapshot="Xưởng chính",
        location_lat_snapshot=Decimal("10.0"),
        location_lng_snapshot=Decimal("106.0"),
        location_radius_m_snapshot=100,
        rate_snapshot=30_000,
        minutes=minutes,
        amount_raw=Decimal(raw),
        status=SessionStatus.closed,
        flags=flags or [],
    )


async def test_report_salary_splits_eligible_and_blocked_pending(pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            employee = EmployeeOrm(code="NV001", full_name="Nguyễn Văn A", role=EmployeeRole.employee, is_active=True)
            manager = EmployeeOrm(code="QL001", full_name="Quản lý", role=EmployeeRole.manager, is_active=True)
            location = WorkLocationOrm(code="KHO01", name="Xưởng chính", latitude=Decimal("10.0"), longitude=Decimal("106.0"), radius_m=100, coordinate_source="manual_coordinates", is_active=True)
            session.add_all([location, employee, manager])
            await session.flush()
            session.add(EmployeeLocationAssignmentOrm(employee_id=employee.id, location_id=location.id, effective_from=dt(6), reason="test default assignment"))
            eligible = closed_session(employee.id, 100_000)
            blocked = closed_session(employee.id, 40_000, ["gps_out_of_range"])
            needs_review = WorkSessionOrm(
                employee_id=employee.id,
                work_date=date(2026, 4, 24),
                check_in_at=dt(12),
                check_in_lat=Decimal("10"),
                check_in_lng=Decimal("106"),
                check_in_accuracy_m=Decimal("10"),
                check_in_distance_m=Decimal("0"),
                work_location_id=location.id,
                location_code_snapshot=location.code,
                location_name_snapshot=location.name,
                location_lat_snapshot=location.latitude,
                location_lng_snapshot=location.longitude,
                location_radius_m_snapshot=location.radius_m,
                rate_snapshot=30_000,
                status=SessionStatus.needs_review,
                review_reason="forgot_checkout",
                flags=[],
            )
            session.add_all([eligible, blocked, needs_review])
            await session.flush()
            employee_id, manager_id, blocked_id = employee.id, manager.id, blocked.id

    async with pg_factory() as session:
        summary = await ReportService(session).summary("day", date(2026, 4, 24))
        payroll_rows = await PayrollService(session).list_payroll(date(2026, 4, 24))
        payroll_a = next(row for row in payroll_rows if row["employee_id"] == employee_id)
        assert summary["pending_eligible"] == 100_000
        assert summary["pending_blocked"] == 40_000
        assert summary["pending"] == 140_000
        assert summary["needs_review_count"] == 1
        assert summary["pending_eligible"] == payroll_a["pending_amount"]

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            await ReviewService(session, FakeClock(dt(13))).mark_flags(manager, blocked_id)

    async with pg_factory() as session:
        summary = await ReportService(session).summary("day", date(2026, 4, 24))
        assert summary["pending_eligible"] == 140_000
        assert summary["pending_blocked"] == 0
        assert summary["needs_review_count"] == 1

    async with pg_factory() as session:
        async with session.begin():
            manager = await session.get(EmployeeOrm, manager_id)
            await PayrollService(session, FakeClock(dt(14))).approve_one(manager, employee_id, date(2026, 4, 24))

    async with pg_factory() as session:
        summary = await ReportService(session).summary("day", date(2026, 4, 24))
        assert summary["paid"] == 140_000
        assert summary["pending_eligible"] == 0
        assert summary["pending_blocked"] == 0
        assert summary["pending"] == 0
        assert summary["needs_review_count"] == 1
