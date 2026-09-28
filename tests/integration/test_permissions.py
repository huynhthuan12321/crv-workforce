import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from source.api.app import setup_api
from source.api.dependencies import get_session
from source.api.utils.session_token import create_session_token
from source.config import settings
from source.database.models import Base, EmployeeLocationAssignmentOrm, EmployeeOrm, OutputLogOrm, ProductOrm, RateHistoryOrm, WorkLocationOrm, WorkSessionOrm
from source.enums import EmployeeRole, SessionStatus
from source.services.rate_limit import attendance_rate_limiter
from source.utils.clock import VIETNAM_TZ


pytestmark = pytest.mark.postgres

NOW = datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ)
ROLES = ("employee", "manager", "director")


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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
async def permission_client(pg_factory):
    app = FastAPI()
    setup_api(app)

    async def override_get_session():
        async with pg_factory() as session:
            async with session.begin():
                yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client, app


async def _reset_db(factory) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with factory() as session:
        async with session.begin():
            await session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


async def _employee(session, code: str, role: EmployeeRole, telegram_id: int) -> EmployeeOrm:
    row = EmployeeOrm(code=code, full_name=code, role=role, telegram_id=telegram_id, is_active=True)
    session.add(row)
    await session.flush()
    return row


@pytest.fixture(scope="module")
async def permission_context(pg_factory, permission_client):
    await clear_rate_limit_state()
    await _reset_db(pg_factory)
    async with pg_factory() as session:
        async with session.begin():
            employee = await _employee(session, "NVPERM", EmployeeRole.employee, 7101)
            manager = await _employee(session, "QLPERM", EmployeeRole.manager, 7102)
            director = await _employee(session, "GDPERM", EmployeeRole.director, 7103)
            managed = await _employee(session, "NVMANAGED", EmployeeRole.employee, 7104)
            location = WorkLocationOrm(code="KHO01", name="Xưởng chính", latitude=Decimal("10"), longitude=Decimal("106"),
                                       radius_m=100, coordinate_source="manual_coordinates", is_active=True)
            session.add(location)
            await session.flush()
            for row_employee in [employee, managed]:
                session.add(EmployeeLocationAssignmentOrm(employee_id=row_employee.id, location_id=location.id,
                                                         effective_from=NOW, reason="test"))
            session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=30_000, effective_from=date.today()))
            product = ProductOrm(code="BOT", name="Bột", kg_per_bag=Decimal("1.20"), sort_order=1)
            session.add(product)
            row = WorkSessionOrm(
                employee_id=employee.id,
                work_date=NOW.date(),
                check_in_at=NOW.replace(hour=7),
                check_out_at=NOW.replace(hour=8),
                check_in_lat=Decimal("10"),
                check_in_lng=Decimal("106"),
                check_in_accuracy_m=Decimal("10"),
                check_in_distance_m=Decimal("0"),
                check_out_lat=Decimal("10"),
                check_out_lng=Decimal("106"),
                check_out_accuracy_m=Decimal("10"),
                check_out_distance_m=Decimal("0"),
                work_location_id=location.id,
                location_code_snapshot=location.code,
                location_name_snapshot=location.name,
                location_lat_snapshot=location.latitude,
                location_lng_snapshot=location.longitude,
                location_radius_m_snapshot=location.radius_m,
                rate_snapshot=30_000,
                minutes=60,
                amount_raw=Decimal("30000"),
                status=SessionStatus.closed,
                flags=["gps_out_of_range"],
            )
            session.add(row)
            await session.flush()
            output = OutputLogOrm(work_session_id=row.id, locked_at=NOW.replace(hour=9))
            session.add(output)
            ids = {"employee": employee.id, "manager": manager.id, "director": director.id, "managed": managed.id, "session": row.id, "location": location.id}

    client, app = permission_client
    yield {"client": client, "ids": ids, "app": app}
    await clear_rate_limit_state()


def token(employee_id: int) -> str:
    return f"Bearer {create_session_token(employee_id)}"


def endpoint_cases(ids: dict) -> list[tuple[str, str, set[str], object]]:
    session_id = ids["session"]
    employee_id = ids["employee"]
    managed_id = ids.get("managed", employee_id)
    location_id = ids.get("location", 1)
    loc = {"lat": 10, "lng": 106, "accuracy_m": 10}
    return [
        ("GET", "/api/auth/me", set(ROLES), None),
        ("GET", "/api/attendance/today", {"employee"}, None),
        ("POST", "/api/attendance/check-in", {"employee"}, loc),
        ("POST", "/api/attendance/check-out", {"employee"}, loc),
        ("GET", "/api/consent/current", {"employee"}, None),
        ("POST", "/api/consent", {"employee"}, {"version": 1}),
        ("POST", "/api/consent/withdraw", {"employee"}, None),
        ("GET", "/api/history", {"employee"}, None),
        ("GET", f"/api/outputs/{session_id}", {"employee"}, None),
        ("PUT", f"/api/outputs/{session_id}", {"employee"}, {"items": {"BOT": 1}}),
        ("GET", "/api/employees", {"manager"}, None),
        ("POST", "/api/employees", {"manager"}, {"code": "NVX", "full_name": "Nhan Vien X", "hourly_rate": 30000, "effective_from": str(date.today()), "location_id": location_id}),
        ("GET", f"/api/employees/{managed_id}", {"manager"}, None),
        ("GET", f"/api/employees/{managed_id}/location-history", {"manager"}, None),
        ("POST", f"/api/employees/{managed_id}/lock", {"manager"}, None),
        ("POST", f"/api/employees/{managed_id}/unlock", {"manager"}, None),
        ("POST", f"/api/employees/{managed_id}/invite", {"manager"}, None),
        ("GET", f"/api/employees/{managed_id}/rates", {"manager"}, None),
        ("POST", f"/api/employees/{managed_id}/rates", {"manager"}, {"hourly_rate": 31000, "effective_from": str(date.today() + timedelta(days=1))}),
        ("GET", "/api/working-now", {"manager"}, None),
        ("GET", "/api/locations", {"manager", "director"}, None),
        ("POST", "/api/locations", {"manager", "director"}, {"code": "KHOX", "name": "Kho X", "latitude": 10.1, "longitude": 106.1, "radius_m": 100, "coordinate_source": "manual_coordinates"}),
        ("PATCH", f"/api/locations/{location_id}", {"manager", "director"}, {"name": "Xưởng chính"}),
        ("POST", f"/api/locations/{location_id}/deactivate", {"manager", "director"}, None),
        ("POST", f"/api/locations/{location_id}/activate", {"manager", "director"}, None),
        ("POST", f"/api/locations/employees/{managed_id}/assignment", {"manager"}, {"location_id": location_id, "reason": "doi kho"}),
        ("GET", "/api/review/pending", {"manager", "director"}, None),
        ("GET", "/api/review/resolved", {"manager", "director"}, None),
        ("POST", f"/api/review/{session_id}/flags-reviewed", {"manager", "director"}, None),
        ("POST", f"/api/review/{session_id}/close", {"manager", "director"}, {"check_out_time": "2026-04-24T08:30:00+07:00", "reason": "dong ca"}),
        ("GET", f"/api/review/{session_id}/checkout-bounds", {"manager", "director"}, None),
        ("PATCH", f"/api/review/{session_id}", {"manager", "director"}, {"check_in_time": "2026-04-24T07:00:00+07:00", "check_out_time": "2026-04-24T08:00:00+07:00", "reason": "sua gio"}),
        ("GET", f"/api/payroll?date={NOW.date()}", {"manager", "director"}, None),
        ("GET", f"/api/payroll/{employee_id}?date={NOW.date()}", {"manager", "director"}, None),
        ("POST", "/api/payroll/approve", {"manager", "director"}, {"date": str(NOW.date()), "employee_ids": [employee_id]}),
        ("GET", f"/api/reports/summary?period=day&date={NOW.date()}", {"director"}, None),
        ("GET", f"/api/reports/products?period=day&date={NOW.date()}", {"director"}, None),
        ("GET", f"/api/reports/timeseries?period=day&date={NOW.date()}", {"director"}, None),
        ("GET", "/api/reports/employees", {"director"}, None),
    ]


def case_ids():
    ids = {"employee": 1, "manager": 2, "director": 3, "managed": 4, "session": 1, "location": 5}
    for method, path, allowed, body in endpoint_cases(ids):
        for role in ROLES:
            yield pytest.param(method, path, allowed, body, role, id=f"{method} {path} as {role}")


@pytest.mark.parametrize(("method", "path", "allowed", "body", "role"), list(case_ids()))
async def test_role_permissions(permission_context, method, path, allowed, body, role):
    client: TestClient = permission_context["client"]
    ids = permission_context["ids"]
    headers = {"Authorization": token(ids[role])}
    response = client.request(method, path, json=body, headers=headers)
    if role in allowed:
        assert response.status_code not in (401, 403), response.text
    else:
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "FORBIDDEN"


async def test_permission_table_covers_all_api_routes(permission_context):
    app: FastAPI = permission_context["app"]
    dummy_ids = {"employee": 111, "manager": 112, "director": 113, "managed": 114, "session": 222, "location": 333}
    documented = {(method, path) for method, path, _, _ in endpoint_cases(dummy_ids)}
    excluded = {
        ("GET", "/api/health"),
        ("POST", "/api/auth/session"),
        ("POST", "/api/auth/redeem-invite"),
    }
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api")
        for method in operations
        if (method.upper(), path) not in excluded
    }
    table_normalized = set()
    for method, path in documented:
        table_normalized.add((method, path.split("?", 1)[0]
                              .replace("111", "{employee_id}")
                              .replace("114", "{employee_id}")
                              .replace("222", "{session_id}")
                              .replace("333", "{location_id}")))
    assert actual == table_normalized
