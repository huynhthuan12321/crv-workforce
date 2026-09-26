import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from source.api.app import setup_api
from source.api.dependencies import get_session
from source.api.utils.session_token import create_session_token
from source.database.models import (
    Base,
    ConsentTextOrm,
    EmployeeOrm,
    LocationConsentOrm,
    OutputLogOrm,
    PayBatchOrm,
    ProductOrm,
    RateHistoryOrm,
    WorkSessionOrm,
)
from source.enums import EmployeeRole, SessionStatus
from source.services import workforce as workforce_module
from source.utils.clock import FakeClock, VIETNAM_TZ


pytestmark = pytest.mark.postgres

NOW = datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ)


@pytest.fixture()
async def pg_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_async_engine(url, pool_pre_ping=True, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def api_client(pg_factory, monkeypatch):
    monkeypatch.setattr(workforce_module, "Clock", lambda: FakeClock(NOW))

    from source.api.routes import consent as consent_route

    monkeypatch.setattr(consent_route, "Clock", lambda: FakeClock(NOW))

    app = FastAPI()
    setup_api(app)

    async def override_get_session():
        async with pg_factory() as session:
            async with session.begin():
                yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client


async def seed_actor(session, code: str, role: EmployeeRole, telegram_id: int | None = None) -> EmployeeOrm:
    row = EmployeeOrm(
        code=code,
        full_name=code,
        role=role,
        telegram_id=telegram_id,
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def seed_rate(session, employee_id: int, rate: int = 30_000, day: date = NOW.date()) -> None:
    session.add(RateHistoryOrm(employee_id=employee_id, hourly_rate=rate, effective_from=day))


async def seed_consent(session, employee_id: int) -> None:
    session.add(LocationConsentOrm(employee_id=employee_id, consent_version=1, consented_at=NOW))


def auth_headers(employee_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_session_token(employee_id)}"}


def work_session(
    employee_id: int,
    *,
    status: SessionStatus = SessionStatus.closed,
    check_in: datetime | None = None,
    check_out: datetime | None = None,
    flags: list[str] | None = None,
) -> WorkSessionOrm:
    check_in = check_in or NOW.replace(hour=7)
    check_out = check_out if check_out is not None else NOW.replace(hour=8)
    minutes = int((check_out - check_in).total_seconds() // 60) if check_out else None
    return WorkSessionOrm(
        employee_id=employee_id,
        work_date=check_in.date(),
        check_in_at=check_in,
        check_out_at=check_out,
        check_in_lat=Decimal("10.0"),
        check_in_lng=Decimal("106.0"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        check_out_lat=Decimal("10.0") if check_out else None,
        check_out_lng=Decimal("106.0") if check_out else None,
        check_out_accuracy_m=Decimal("10") if check_out else None,
        check_out_distance_m=Decimal("0") if check_out else None,
        rate_snapshot=30_000,
        minutes=minutes,
        amount_raw=(Decimal(minutes) * Decimal(30_000) / Decimal(60)) if minutes is not None else None,
        status=status,
        flags=flags or [],
    )


async def test_http_write_endpoints_succeed_on_postgres(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            session.add(ConsentTextOrm(version=1, content="consent", effective_at=NOW - timedelta(days=1)))
            for idx, code in enumerate(["BOT", "XUC_XICH", "PHO_MAI", "CHA_BONG", "SOT_CAM", "SOT_TRANG", "BO"], start=1):
                session.add(ProductOrm(code=code, name=code, kg_per_bag=Decimal("1.00"), sort_order=idx))
            employee = await seed_actor(session, "NV001", EmployeeRole.employee, 1001)
            manager = await seed_actor(session, "QL001", EmployeeRole.manager, 2001)
            await seed_rate(session, employee.id)
            employee_id, manager_id = employee.id, manager.id

    employee_headers = auth_headers(employee_id)
    manager_headers = auth_headers(manager_id)
    loc = {"lat": 10.0, "lng": 106.0, "accuracy_m": 10}

    response = api_client.post("/api/consent", json={"version": 1}, headers=employee_headers)
    assert response.status_code == 200, response.text

    response = api_client.post("/api/consent/withdraw", headers=employee_headers)
    assert response.status_code == 200, response.text

    response = api_client.post("/api/consent", json={"version": 1}, headers=employee_headers)
    assert response.status_code == 200, response.text

    response = api_client.post("/api/attendance/check-in", json=loc, headers=employee_headers)
    assert response.status_code == 200, response.text
    checked_session_id = response.json()["data"]["id"]

    response = api_client.post("/api/attendance/check-out", json=loc, headers=employee_headers)
    assert response.status_code == 200, response.text

    response = api_client.put(
        f"/api/outputs/{checked_session_id}",
        json={"items": {"BOT": 1, "XUC_XICH": 1}},
        headers=employee_headers,
    )
    assert response.status_code == 200, response.text

    async with pg_factory() as session:
        async with session.begin():
            flagged = work_session(employee_id, flags=["gps_out_of_range"])
            session.add(flagged)
            forgotten = work_session(
                employee_id,
                status=SessionStatus.needs_review,
                check_in=NOW.replace(hour=7),
                check_out=None,
            )
            forgotten.review_reason = "forgot_checkout"
            session.add(forgotten)
            editable = work_session(employee_id, check_in=NOW.replace(hour=9), check_out=NOW.replace(hour=10))
            session.add(editable)
            payable = work_session(employee_id, check_in=NOW.replace(hour=11), check_out=NOW.replace(hour=12))
            session.add(payable)
            await session.flush()
            flagged_id, forgotten_id, editable_id = flagged.id, forgotten.id, editable.id

    response = api_client.post(f"/api/review/{flagged_id}/flags-reviewed", headers=manager_headers)
    assert response.status_code == 200, response.text

    response = api_client.post(
        f"/api/review/{forgotten_id}/close",
        json={"check_out_time": "2026-04-24T08:30:00+07:00", "reason": "quan ly dong ca"},
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text

    response = api_client.patch(
        f"/api/review/{editable_id}",
        json={
            "check_in_time": "2026-04-24T09:15:00+07:00",
            "check_out_time": "2026-04-24T10:15:00+07:00",
            "reason": "dieu chinh gio",
        },
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text

    response = api_client.post(
        "/api/payroll/approve",
        json={"date": str(NOW.date()), "employee_ids": [employee_id]},
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]

    response = api_client.post(
        "/api/employees",
        json={"code": "NVHTTP", "full_name": "Nhan vien HTTP", "hourly_rate": 30_000, "effective_from": str(date.today())},
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text
    managed_employee_id = response.json()["data"]["id"]

    response = api_client.post(f"/api/employees/{managed_employee_id}/lock", headers=manager_headers)
    assert response.status_code == 200, response.text

    response = api_client.post(f"/api/employees/{managed_employee_id}/unlock", headers=manager_headers)
    assert response.status_code == 200, response.text

    response = api_client.post(
        f"/api/employees/{managed_employee_id}/rates",
        json={"hourly_rate": 31_000, "effective_from": str(date.today() + timedelta(days=1))},
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text

    response = api_client.post(f"/api/employees/{managed_employee_id}/invite", headers=manager_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["invite_url"]


async def test_http_business_error_rolls_back(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            session.add(ConsentTextOrm(version=1, content="consent", effective_at=NOW - timedelta(days=1)))
            employee = await seed_actor(session, "NVROLL", EmployeeRole.employee, 3001)
            await seed_rate(session, employee.id)
            await seed_consent(session, employee.id)
            employee_id = employee.id

    headers = auth_headers(employee_id)
    loc = {"lat": 10.0, "lng": 106.0, "accuracy_m": 10}

    response = api_client.post("/api/attendance/check-in", json=loc, headers=headers)
    assert response.status_code == 200, response.text

    async with pg_factory() as session:
        before = await session.scalar(select(func.count()).select_from(WorkSessionOrm))

    response = api_client.post("/api/attendance/check-in", json=loc, headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "SESSION_ALREADY_OPEN"

    async with pg_factory() as session:
        after = await session.scalar(select(func.count()).select_from(WorkSessionOrm))
        open_count = await session.scalar(
            select(func.count()).select_from(WorkSessionOrm).where(
                WorkSessionOrm.employee_id == employee_id,
                WorkSessionOrm.status == SessionStatus.open,
            ),
        )
        assert before == after
        assert open_count == 1
