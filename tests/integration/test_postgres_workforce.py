import os
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from source.database.models import Base, EmployeeOrm, PayBatchOrm, WorkSessionOrm
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import PayrollService, ReviewService
from source.utils.clock import FakeClock, VIETNAM_TZ


pytestmark = pytest.mark.postgres


def dt(hour: int, minute: int = 0):
    from datetime import datetime

    return datetime(2026, 4, 24, hour, minute, tzinfo=VIETNAM_TZ)


@pytest.fixture()
async def pg_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_async_engine(url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def make_employee(session, code="NV001", role=EmployeeRole.employee):
    row = EmployeeOrm(code=code, full_name=code, role=role, is_active=True)
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
            actor = await session.get(EmployeeOrm, manager_id)
            try:
                async with session.begin():
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
            actor = await session.get(EmployeeOrm, manager_id)
            try:
                async with session.begin():
                    return await ReviewService(session, FakeClock(dt(20))).close_forgotten(
                        actor, session_id, dt(17), "quên bấm ra ca"
                    )
            except WorkforceError as exc:
                return exc.code

    results = await asyncio.gather(close_once(), close_once())
    assert sum(isinstance(item, WorkSessionOrm) for item in results) == 1
    assert results.count("ALREADY_HANDLED") == 1
