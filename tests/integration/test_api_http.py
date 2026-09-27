import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from source.api.app import setup_api
from source.api.dependencies import get_session
from source.api.utils.session_token import create_session_token
from source.config import settings
from source.database.models import (
    Base,
    ConsentTextOrm,
    EmployeeOrm,
    LocationConsentOrm,
    OutputLogOrm,
    OutputItemOrm,
    PayBatchOrm,
    ProductOrm,
    RateHistoryOrm,
    WorkSessionOrm,
    NotificationOutboxOrm,
    AuditLogOrm,
)
from source.enums import EmployeeRole, SessionStatus
from source.services.rate_limit import attendance_rate_limiter
from source.services import workforce as workforce_module
from source.utils.clock import FakeClock, VIETNAM_TZ
from source.workers import reminder_job, notification_text


pytestmark = pytest.mark.postgres

NOW = datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ)


async def clear_rate_limit_state() -> None:
    attendance_rate_limiter.reset_memory()
    if os.getenv("CRV_TEST_CLEAR_REDIS") != "1":
        return
    redis = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        username=settings.redis.user,
        password=settings.redis.password.get_secret_value(),
        db=settings.redis.db,
        decode_responses=True,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
    )
    try:
        keys = [key async for key in redis.scan_iter(match="rl:attendance:*")]
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass
    finally:
        await redis.aclose()


@pytest.fixture()
async def pg_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        if os.getenv("CRV_REQUIRE_POSTGRES") == "1":
            pytest.fail("CRV_REQUIRE_POSTGRES=1 but TEST_DATABASE_URL is not set")
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
    await clear_rate_limit_state()
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
        await clear_rate_limit_state()
        yield client
    await clear_rate_limit_state()


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

    await clear_rate_limit_state()
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


async def test_today_returns_vn_timezone_and_reminder_uses_vn_time(api_client, pg_factory):
    check_in = datetime(2026, 4, 24, 8, 12, tzinfo=VIETNAM_TZ)
    async with pg_factory() as session:
        async with session.begin():
            session.add(ConsentTextOrm(version=1, content="consent", effective_at=NOW - timedelta(days=1)))
            employee = await seed_actor(session, "NVTZ", EmployeeRole.employee, 4001)
            await seed_rate(session, employee.id)
            await seed_consent(session, employee.id)
            row = work_session(employee.id, status=SessionStatus.open, check_in=check_in, check_out=None)
            session.add(row)
            employee_id = employee.id

    response = api_client.get("/api/attendance/today", headers=auth_headers(employee_id))
    assert response.status_code == 200, response.text
    check_in_at = response.json()["data"]["open_session"]["check_in_at"]
    assert check_in_at.endswith("+07:00")
    assert "T08:12:" in check_in_at

    await reminder_job(pg_factory, FakeClock(datetime(2026, 4, 24, 18, 0, tzinfo=VIETNAM_TZ)))
    async with pg_factory() as session:
        notice = await session.scalar(select(NotificationOutboxOrm).where(NotificationOutboxOrm.notification_type == "checkout_reminder"))
        assert notice is not None
        assert "08:12" in notification_text(notice)


async def test_report_salary_uses_daily_paid_plus_pending_not_period_raw_ceiling(api_client, pg_factory):
    day1 = date(2026, 4, 24)
    day2 = date(2026, 4, 25)
    async with pg_factory() as session:
        async with session.begin():
            director = await seed_actor(session, "GD001", EmployeeRole.director, 5001)
            employee = await seed_actor(session, "NVREP", EmployeeRole.employee, 5002)
            s1 = work_session(employee.id, check_in=datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ),
                              check_out=datetime(2026, 4, 24, 13, 23, tzinfo=VIETNAM_TZ))
            s1.amount_raw = Decimal("161500")
            s2 = work_session(employee.id, check_in=datetime(2026, 4, 25, 8, 0, tzinfo=VIETNAM_TZ),
                              check_out=datetime(2026, 4, 25, 13, 5, tzinfo=VIETNAM_TZ))
            s2.amount_raw = Decimal("152500")
            session.add_all([s1, s2])
            await session.flush()
            batch = PayBatchOrm(employee_id=employee.id, work_date=day1, batch_no=1, amount=162000,
                                day_total_rounded_at_approval=162000, status="paid", approved_by=director.id,
                                approved_at=NOW)
            session.add(batch)
            await session.flush()
            s1.pay_batch_id = batch.id
            director_id = director.id

    response = api_client.get("/api/reports/summary?period=week&date=2026-04-24", headers=auth_headers(director_id))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["paid"] == 162000
    assert data["pending"] == 153000
    assert data["total"] == 315000
    assert data["total"] != 314000
    assert data["from"] == "2026-04-20"
    assert data["to"] == "2026-04-26"


async def test_director_report_employees_search(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            director = await seed_actor(session, "GDREP", EmployeeRole.director, 7001)
            await seed_actor(session, "NV001", EmployeeRole.employee, 7002)
            await seed_actor(session, "NV002", EmployeeRole.employee, 7003)
            await seed_actor(session, "QL001", EmployeeRole.manager, 7004)
            director_id = director.id
    response = api_client.get("/api/reports/employees?q=NV001", headers=auth_headers(director_id))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [(row["code"], row["full_name"]) for row in data] == [("NV001", "NV001")]
    assert "current_hourly_rate" not in data[0]


async def test_history_grouped_by_day_shows_batch_money_and_output(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            session.add(ConsentTextOrm(version=1, content="consent", effective_at=NOW - timedelta(days=1)))
            product = ProductOrm(code="BOT", name="Bột", kg_per_bag=Decimal("1.20"), sort_order=1)
            session.add(product)
            employee = await seed_actor(session, "NVHIS", EmployeeRole.employee, 6001)
            manager = await seed_actor(session, "QLHIS", EmployeeRole.manager, 6002)
            row = work_session(employee.id, check_in=NOW.replace(hour=7), check_out=NOW.replace(hour=8))
            session.add(row)
            await session.flush()
            output = OutputLogOrm(work_session_id=row.id, submitted_at=NOW, locked_at=NOW + timedelta(minutes=10))
            session.add(output)
            await session.flush()
            session.add(OutputItemOrm(output_log_id=output.id, product_id=product.id, bags=5, kg=Decimal("6.00")))
            employee_id, manager_id = employee.id, manager.id

    response = api_client.post("/api/payroll/approve", json={"date": str(NOW.date()), "employee_ids": [employee_id]},
                               headers=auth_headers(manager_id))
    assert response.status_code == 200, response.text

    response = api_client.get("/api/history", headers=auth_headers(employee_id))
    assert response.status_code == 200, response.text
    day = response.json()["data"]["days"][0]
    assert day["batches"][0]["amount"] == 30000
    assert day["batches"][0]["sessions"][0]["output"][0]["bags"] == 5


async def test_gd7c_manager_api_fields_and_filters(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            employee = await seed_actor(session, "NV007", EmployeeRole.employee, 7001)
            manager = await seed_actor(session, "QL007", EmployeeRole.manager, 7002)
            await seed_rate(session, employee.id, 30_000)
            flagged = work_session(employee.id, flags=["gps_out_of_range"])
            flagged.check_in_accuracy_m = Decimal("35")
            flagged.check_in_distance_m = Decimal("150")
            forgotten = work_session(employee.id, status=SessionStatus.needs_review, check_out=None)
            forgotten.review_reason = "forgot_checkout"
            open_row = work_session(employee.id, status=SessionStatus.open, check_in=NOW.replace(hour=9), check_out=None)
            open_row.check_in_distance_m = Decimal("150")
            open_row.check_in_accuracy_m = Decimal("40")
            open_row.flags = ["gps_out_of_range"]
            session.add_all([flagged, forgotten, open_row])
            await session.flush()
            employee_id, manager_id = employee.id, manager.id
            flagged_id = flagged.id
            forgotten_id = forgotten.id

    headers = auth_headers(manager_id)

    response = api_client.get("/api/review/pending?type=gps", headers=headers)
    assert response.status_code == 200, response.text
    gps = response.json()["data"]
    assert len(gps) == 1
    assert gps[0]["employee_code"] == "NV007"
    assert gps[0]["employee_name"] == "NV007"
    assert gps[0]["check_in_accuracy_m"] is not None
    assert gps[0]["check_in_distance_m"] is not None

    response = api_client.get("/api/review/pending?type=forgot", headers=headers)
    assert response.status_code == 200, response.text
    forgot = response.json()["data"]
    assert [item["id"] for item in forgot] == [forgotten_id]
    assert forgot[0]["review_reason"] == "forgot_checkout"

    response = api_client.post(f"/api/review/{flagged_id}/flags-reviewed", headers=headers)
    assert response.status_code == 200, response.text
    response = api_client.post(f"/api/review/{flagged_id}/flags-reviewed", headers=headers)
    assert response.status_code == 409
    assert response.json()["details"]["handled_by_name"] == "QL007"
    assert response.json()["details"]["action"] == "flags_reviewed"

    response = api_client.get("/api/review/resolved?type=gps", headers=headers)
    assert response.status_code == 200, response.text
    resolved = response.json()["data"][0]
    assert resolved["resolved_by_name"] == "QL007"
    assert resolved["resolved_at"].endswith("+07:00")
    assert resolved["resolved_action"] == "flags_reviewed"

    response = api_client.get("/api/working-now", headers=headers)
    assert response.status_code == 200, response.text
    working = response.json()["data"][0]
    assert working["check_in_distance_m"] == 150.0
    assert working["check_in_accuracy_m"] == 40.0
    assert working["is_outside"] is True

    response = api_client.get(f"/api/payroll?date={NOW.date()}", headers=headers)
    assert response.status_code == 200, response.text
    payroll = response.json()["data"][0]
    assert payroll["hourly_rate"] == 30000
    assert payroll["has_open_session"] is True
    assert payroll["needs_review_session_ids"] == [forgotten_id]
    assert payroll["pending_reason"] == "open_session"

    response = api_client.get(f"/api/payroll/{employee_id}?date={NOW.date()}", headers=headers)
    assert response.status_code == 200, response.text
    detail = response.json()["data"]
    assert "is_locked" in detail["sessions"][0]

    response = api_client.get("/api/employees?q=NV007&active=true", headers=headers)
    assert response.status_code == 200, response.text
    managed = response.json()["data"][0]
    assert managed["current_hourly_rate"] == 30000
    assert managed["is_linked"] is True
    assert managed["has_open_session"] is True


async def test_gd7c_employee_admin_errors_audit_and_rate_conflict(api_client, pg_factory):
    async with pg_factory() as session:
        async with session.begin():
            manager = await seed_actor(session, "QL008", EmployeeRole.manager, 8001)
            employee = await seed_actor(session, "NV008", EmployeeRole.employee, None)
            await seed_rate(session, employee.id, 28_000)
            employee_id, manager_id = employee.id, manager.id

    headers = auth_headers(manager_id)

    response = api_client.post("/api/employees/999999/lock", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "EMPLOYEE_NOT_FOUND"

    response = api_client.post(f"/api/employees/{manager_id}/lock", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"

    response = api_client.post(
        f"/api/employees/{employee_id}/rates",
        json={"hourly_rate": 29_000, "effective_from": str(NOW.date())},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "RATE_DATE_EXISTS"

    response = api_client.post(f"/api/employees/{employee_id}/lock", headers=headers)
    assert response.status_code == 200, response.text
    response = api_client.post(f"/api/employees/{employee_id}/unlock", headers=headers)
    assert response.status_code == 200, response.text
    response = api_client.post(f"/api/employees/{employee_id}/invite", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["invite_url"]

    async with pg_factory() as session:
        actions = (await session.execute(
            select(func.count()).select_from(AuditLogOrm).where(
                AuditLogOrm.action.in_(["employee_locked", "employee_unlocked", "invite_regenerated"]),
            ),
        )).scalar_one()
        assert actions == 3
