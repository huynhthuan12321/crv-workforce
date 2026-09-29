from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from source.api.routes import review as review_routes
from source.database.models import (
    AuditLogOrm,
    ConsentTextOrm,
    EmployeeOrm,
    LocationConsentOrm,
    NotificationOutboxOrm,
    OutputItemOrm,
    OutputLogOrm,
    PayBatchOrm,
    ProductOrm,
    RateHistoryOrm,
    SyncOutboxOrm,
    EmployeeLocationAssignmentOrm,
    WorkLocationOrm,
    WorkSessionOrm,
)
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole, SessionStatus
from source.services.workforce import (
    AttendanceService,
    HistoryService,
    OutputService,
    PayrollService,
    ReviewService,
    WorkLocationService,
    session_dict,
)
from source.utils.clock import FakeClock, VIETNAM_TZ
from source.workers import notification_text


def dt(hour: int, minute: int = 0, second: int = 0, day: int = 24) -> datetime:
    return datetime(2026, 4, day, hour, minute, second, tzinfo=VIETNAM_TZ)


def utc_dt(hour: int, minute: int = 0, second: int = 0, day: int = 24) -> datetime:
    return datetime(2026, 4, day, hour, minute, second, tzinfo=timezone.utc)


async def make_employee(
    session,
    code: str = "NV001",
    name: str = "Nguyễn Văn A",
    rate: int = 30_000,
    role: EmployeeRole = EmployeeRole.employee,
) -> EmployeeOrm:
    location = await session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.code == "KHO01"))
    if not location:
        location = WorkLocationOrm(code="KHO01", name="Xưởng chính", latitude=Decimal("10.0"),
                                   longitude=Decimal("106.0"), radius_m=100,
                                   coordinate_source="manual_coordinates", is_active=True)
        session.add(location)
        await session.flush()
    employee = EmployeeOrm(code=code, full_name=name, role=role, is_active=True)
    session.add(employee)
    await session.flush()
    session.add(RateHistoryOrm(
        employee_id=employee.id,
        hourly_rate=rate,
        effective_from=date(2026, 1, 1),
    ))
    if role == EmployeeRole.employee:
        session.add(EmployeeLocationAssignmentOrm(employee_id=employee.id, location_id=location.id,
                                                 effective_from=dt(0, 0), reason="test"))
    await session.flush()
    return employee


async def add_consent(session, employee: EmployeeOrm, now: datetime = dt(6, 0)) -> None:
    session.add(ConsentTextOrm(version=1, content="consent v1", effective_at=now - timedelta(days=1)))
    await session.flush()
    session.add(LocationConsentOrm(
        employee_id=employee.id,
        consent_version=1,
        consented_at=now,
    ))
    await session.flush()


async def add_products(session) -> None:
    products = [
        ("BOT", "Bột", Decimal("1.2"), 1),
        ("XUC_XICH", "Xúc xích", Decimal("1"), 2),
        ("PHO_MAI", "Phô mai", Decimal("1"), 3),
        ("CHA_BONG", "Chà bông", Decimal("1"), 4),
        ("SOT_CAM", "Sốt cam", Decimal("2"), 5),
        ("SOT_TRANG", "Sốt trắng", Decimal("2"), 6),
        ("BO", "Bơ", Decimal("2"), 7),
    ]
    for code, name, kg, order in products:
        session.add(ProductOrm(code=code, name=name, kg_per_bag=kg, sort_order=order))
    await session.flush()


def assert_code(exc_info, code: str) -> None:
    assert isinstance(exc_info.value, WorkforceError)
    assert exc_info.value.code == code


async def closed_session(
    session,
    employee: EmployeeOrm,
    check_in: datetime,
    check_out: datetime,
    rate: int = 30_000,
    flags: list[str] | None = None,
    pay_batch_id: int | None = None,
) -> WorkSessionOrm:
    minutes = int((check_out - check_in).total_seconds() // 60)
    row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=check_in.date(),
        check_in_at=check_in,
        check_out_at=check_out,
        check_in_lat=Decimal("10.0"),
        check_in_lng=Decimal("106.0"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        check_out_lat=Decimal("10.0"),
        check_out_lng=Decimal("106.0"),
        check_out_accuracy_m=Decimal("10"),
        check_out_distance_m=Decimal("0"),
        work_location_id=1,
        location_code_snapshot="KHO01",
        location_name_snapshot="Xưởng chính",
        location_lat_snapshot=Decimal("10.0"),
        location_lng_snapshot=Decimal("106.0"),
        location_radius_m_snapshot=100,
        rate_snapshot=rate,
        minutes=minutes,
        amount_raw=Decimal(minutes) * Decimal(rate) / Decimal(60),
        status=SessionStatus.closed,
        flags=flags or [],
        pay_batch_id=pay_batch_id,
    )
    session.add(row)
    await session.flush()
    return row


@pytest.mark.unit
async def test_attendance_checkin_cutoff_open_gps_money_rate_and_consent(session):
    employee = await make_employee(session)
    await add_consent(session, employee, dt(6, 0))

    row = await AttendanceService(session, FakeClock(dt(17, 59, 59))).check_in(employee, 10.0, 106.0, 10)
    assert row.status == SessionStatus.open

    with pytest.raises(WorkforceError) as exc:
        await AttendanceService(session, FakeClock(dt(18, 0, 0))).check_in(employee, 10.0, 106.0, 10)
    assert_code(exc, "CHECKIN_AFTER_CUTOFF")

    with pytest.raises(WorkforceError) as exc:
        await AttendanceService(session, FakeClock(dt(17, 0, 0))).check_in(employee, 10.0, 106.0, 10)
    assert_code(exc, "SESSION_ALREADY_OPEN")

    row.check_out_at = dt(11, 35)
    row.status = SessionStatus.closed
    row.minutes = 323
    row.amount_raw = Decimal("161500")
    await session.flush()

    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=99_000, effective_from=date(2026, 4, 25)))
    await session.flush()
    second = await AttendanceService(session, FakeClock(dt(13, 5))).check_in(employee, 10.0, 106.0, 10)
    assert second.rate_snapshot == 30_000

    no_consent = await make_employee(session, "NV009", "Chưa đồng ý")
    with pytest.raises(WorkforceError) as exc:
        await AttendanceService(session, FakeClock(dt(9, 0))).check_in(no_consent, 10.0, 106.0, 10)
    assert_code(exc, "LOCATION_CONSENT_REQUIRED")


@pytest.mark.unit
async def test_attendance_gps_flags_previous_review_does_not_block(session):
    employee = await make_employee(session)
    await add_consent(session, employee, dt(6, 0))
    session.add(WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 23),
        check_in_at=dt(9, 0, day=23),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        flags=[],
    ))
    await session.flush()

    row = await AttendanceService(session, FakeClock(dt(8, 0))).check_in(employee, 10.00135, 106.0, 250)
    assert set(row.flags) == {"gps_out_of_range", "gps_low_accuracy"}

    assert row.status == SessionStatus.open


@pytest.mark.unit
async def test_attendance_unknown_gps_accuracy_is_flagged_for_review(session):
    employee = await make_employee(session)
    await add_consent(session, employee, dt(6, 0))

    row = await AttendanceService(session, FakeClock(dt(8, 0))).check_in(employee, 10.0, 106.0, None)

    assert row.check_in_accuracy_m is None
    assert row.flags == ["gps_accuracy_unknown"]
    assert row.flag_source == "check_in"


@pytest.mark.unit
async def test_location_gps_unknown_accuracy_requires_confirmation_and_audits(session):
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    service = WorkLocationService(session, FakeClock(dt(8, 0)))

    with pytest.raises(WorkforceError) as exc:
        await service.create(manager, "KHO02", "Kho 02", None, 10.0, 106.0, 100, "device_gps", None, False)
    assert_code(exc, "LOCATION_INVALID")
    assert exc.value.details["reason"] == "low_accuracy_requires_confirmation"

    created = await service.create(manager, "KHO02", "Kho 02", None, 10.0, 106.0, 100, "device_gps", None, True)
    audit = await session.scalar(select(AuditLogOrm).where(AuditLogOrm.action == "location_saved_with_low_accuracy"))

    assert created["code"] == "KHO02"
    assert created["location_accuracy_m"] is None
    assert audit is not None
    assert audit.new_value["accuracy_m"] is None


@pytest.mark.unit
async def test_check_out_rollback_keeps_session_open_and_no_outbox(session_factory):
    async with session_factory() as setup_session:
        async with setup_session.begin():
            employee = await make_employee(setup_session)
            await add_consent(setup_session, employee, dt(6, 0))
            row = await AttendanceService(setup_session, FakeClock(dt(8, 0))).check_in(employee, 10.0, 106.0, 10)
            employee_id = employee.id
            session_id = row.id

    with pytest.raises(RuntimeError):
        async with session_factory() as tx_session:
            async with tx_session.begin():
                employee = await tx_session.get(EmployeeOrm, employee_id)
                await AttendanceService(tx_session, FakeClock(dt(11, 35))).check_out(employee, 10.0, 106.0, 10)
                raise RuntimeError("force rollback before commit")

    async with session_factory() as verify_session:
        row = await verify_session.get(WorkSessionOrm, session_id)
        assert row.status == SessionStatus.open
        assert row.check_out_at is None
        assert (await verify_session.scalars(select(SyncOutboxOrm))).all() == []


@pytest.mark.unit
async def test_attendance_323_minutes_amount_raw(session):
    employee = await make_employee(session)
    await add_consent(session, employee, dt(6, 0))
    row = await AttendanceService(session, FakeClock(dt(6, 12))).check_in(employee, 10.0, 106.0, 10)
    await AttendanceService(session, FakeClock(dt(11, 35))).check_out(employee, 10.0, 106.0, 10)
    assert row.minutes == 323
    assert row.amount_raw == Decimal("161500.0000")


@pytest.mark.unit
async def test_output_total_lock_boundary_and_owner(session):
    owner = await make_employee(session)
    other = await make_employee(session, "NV002", "Người khác")
    await add_products(session)
    work = await closed_session(session, owner, dt(6, 12), dt(11, 35))
    session.add(OutputLogOrm(work_session_id=work.id, locked_at=dt(11, 45)))
    await session.flush()

    values = {"BOT": 5, "XUC_XICH": 3, "PHO_MAI": 2, "CHA_BONG": 1, "SOT_CAM": 1}
    result = await OutputService(session, FakeClock(dt(11, 44, 59))).submit(owner, work.id, values)
    assert result["total_kg"] == 14.0
    assert len((await session.scalars(select(OutputItemOrm))).all()) == 7

    with pytest.raises(WorkforceError) as exc:
        await OutputService(session, FakeClock(dt(11, 45))).submit(owner, work.id, values)
    assert_code(exc, "OUTPUT_LOCKED")

    with pytest.raises(WorkforceError) as exc:
        await OutputService(session, FakeClock(dt(11, 44))).submit(other, work.id, values)
    assert_code(exc, "NOT_OWNER")


@pytest.mark.unit
async def test_review_close_edit_resolved_and_sweep(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    flagged = await closed_session(session, employee, dt(7, 0), dt(8, 0), flags=["gps_low_accuracy"])

    await ReviewService(session, FakeClock(dt(9, 0))).mark_flags(manager, flagged.id)
    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session, FakeClock(dt(9, 1))).mark_flags(manager, flagged.id)
    assert_code(exc, "ALREADY_HANDLED")

    resolved = await ReviewService(session).list_resolved()
    assert resolved[0]["resolved_by_name"] == "Quản lý"

    forgotten = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(8, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(forgotten)
    await session.flush()

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).close_forgotten(manager, forgotten.id, dt(7, 59), "sai giờ")
    assert_code(exc, "INVALID_CHECKOUT_TIME")

    closed = await ReviewService(session, FakeClock(dt(20, 0))).close_forgotten(manager, forgotten.id, dt(17, 0), "quên bấm ra ca")
    output = await session.scalar(select(OutputLogOrm).where(OutputLogOrm.work_session_id == closed.id))
    assert output.locked_at == dt(20, 10).replace(tzinfo=None)

    paid_batch = PayBatchOrm(employee_id=employee.id, work_date=date(2026, 4, 24), batch_no=1, amount=10_000, day_total_rounded_at_approval=10_000, approved_by=manager.id)
    session.add(paid_batch)
    await session.flush()
    paid = await closed_session(session, employee, dt(13, 0), dt(14, 0), pay_batch_id=paid_batch.id)
    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).edit_session(manager, paid.id, dt(13, 0), dt(14, 30), "sửa phiên đã trả")
    assert_code(exc, "SESSION_LOCKED_PAID")

    open_row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 21),
        check_in_at=dt(8, 0, day=21),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    )
    session.add(open_row)
    await session.flush()
    swept = await ReviewService(session, FakeClock(dt(0, 5))).sweep_stale()
    assert swept[0].status == SessionStatus.needs_review


@pytest.mark.unit
async def test_closed_forgotten_session_moves_from_pending_to_resolved(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    forgotten = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(8, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(forgotten)
    await session.flush()

    await ReviewService(session, FakeClock(dt(19, 24))).close_forgotten(manager, forgotten.id, dt(17, 0), "quên bấm ra ca")

    pending = await ReviewService(session).pending("forgot")
    resolved = await ReviewService(session).list_resolved("forgot")
    assert [row["id"] for row in pending] == []
    assert [row["id"] for row in resolved] == [forgotten.id]


@pytest.mark.unit
async def test_close_forgotten_rejects_future_and_overlap_with_max_checkout_details(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    first = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 9, 27),
        check_in_at=datetime(2026, 9, 27, 9, 59, tzinfo=VIETNAM_TZ),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    second = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 9, 27),
        check_in_at=datetime(2026, 9, 27, 17, 49, tzinfo=VIETNAM_TZ),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    open_row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 9, 27),
        check_in_at=datetime(2026, 9, 27, 19, 21, tzinfo=VIETNAM_TZ),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    )
    session.add_all([first, second, open_row])
    await session.flush()
    service = ReviewService(session, FakeClock(datetime(2026, 9, 27, 19, 24, tzinfo=VIETNAM_TZ)))

    with pytest.raises(WorkforceError) as exc:
        await service.close_forgotten(manager, first.id, datetime(2026, 9, 27, 20, 0, tzinfo=VIETNAM_TZ), "quên bấm ra ca")
    assert_code(exc, "CHECKOUT_IN_FUTURE")
    assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"

    with pytest.raises(WorkforceError) as exc:
        await service.close_forgotten(manager, first.id, datetime(2026, 9, 27, 18, 0, tzinfo=VIETNAM_TZ), "quên bấm ra ca")
    assert_code(exc, "SESSION_OVERLAP")
    assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"
    assert exc.value.details["overlap"]["id"] == second.id

    bounds = await service.checkout_bounds(second.id)
    assert bounds["max_check_out"] == "2026-09-27T19:21:00+07:00"
    assert [row["id"] for row in bounds["sessions"]] == [first.id, open_row.id]

    with pytest.raises(WorkforceError) as exc:
        await service.close_forgotten(manager, second.id, datetime(2026, 9, 27, 19, 22, tzinfo=VIETNAM_TZ), "quên bấm ra ca")
    assert_code(exc, "SESSION_OVERLAP")
    assert exc.value.details["max_check_out"] == "2026-09-27T19:21:00+07:00"
    assert exc.value.details["overlap"]["id"] == open_row.id
    assert exc.value.details["overlap"]["check_out_at"] is None


@pytest.mark.unit
async def test_edit_session_rejects_future_and_overlap_like_close_forgotten(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    editable = await closed_session(
        session,
        employee,
        datetime(2026, 9, 27, 9, 59, tzinfo=VIETNAM_TZ),
        datetime(2026, 9, 27, 10, 10, tzinfo=VIETNAM_TZ),
    )
    next_row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 9, 27),
        check_in_at=datetime(2026, 9, 27, 17, 49, tzinfo=VIETNAM_TZ),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(next_row)
    await session.flush()
    service = ReviewService(session, FakeClock(datetime(2026, 9, 27, 19, 24, tzinfo=VIETNAM_TZ)))

    with pytest.raises(WorkforceError) as exc:
        await service.edit_session(
            manager,
            editable.id,
            datetime(2026, 9, 27, 9, 59, tzinfo=VIETNAM_TZ),
            datetime(2026, 9, 27, 20, 0, tzinfo=VIETNAM_TZ),
            "sửa theo thực tế",
        )
    assert_code(exc, "CHECKOUT_IN_FUTURE")

    with pytest.raises(WorkforceError) as exc:
        await service.edit_session(
            manager,
            editable.id,
            datetime(2026, 9, 27, 9, 59, tzinfo=VIETNAM_TZ),
            datetime(2026, 9, 27, 18, 0, tzinfo=VIETNAM_TZ),
            "sửa theo thực tế",
        )
    assert_code(exc, "SESSION_OVERLAP")
    assert exc.value.details["max_check_out"] == "2026-09-27T17:49:00+07:00"


@pytest.mark.unit
async def test_escalate_1830(session):
    employee = await make_employee(session)
    other_employee = await make_employee(session, "NV002", "Nhân viên hôm qua")
    today_open = WorkSessionOrm(
        employee_id=other_employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(8, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    )
    yesterday_open = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 23),
        check_in_at=dt(8, 0, day=23),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    )
    closed = await closed_session(session, employee, dt(9, 0), dt(10, 0))
    session.add_all([today_open, yesterday_open])
    await session.flush()

    rows = await ReviewService(session, FakeClock(dt(18, 30))).escalate()

    assert rows == [today_open]
    assert today_open.status == SessionStatus.needs_review
    assert today_open.review_reason == "forgot_checkout"
    assert yesterday_open.status == SessionStatus.open
    assert closed.status == SessionStatus.closed


@pytest.mark.unit
async def test_review_edit_session_audit_outbox_and_overlap(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    first = await closed_session(session, employee, dt(8, 0), dt(9, 0))
    await closed_session(session, employee, dt(10, 0), dt(11, 0))

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).edit_session(manager, first.id, dt(8, 30), dt(10, 30), "bị chồng giờ")
    assert_code(exc, "SESSION_OVERLAP")

    edited = await ReviewService(session).edit_session(manager, first.id, dt(7, 30), dt(9, 0), "sửa theo sổ giấy")
    assert edited.minutes == 90
    assert edited.amount_raw == Decimal("45000.0000")
    assert await session.scalar(select(AuditLogOrm).where(AuditLogOrm.action == "session_edit"))
    assert await session.scalar(select(SyncOutboxOrm).where(SyncOutboxOrm.event_type == "session_updated"))


@pytest.mark.unit
async def test_edit_session_accepts_utc_input(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    row = await closed_session(session, employee, dt(7, 0), dt(8, 0))

    edited = await ReviewService(session).edit_session(
        manager,
        row.id,
        utc_dt(23, 0, day=23),
        utc_dt(1, 0),
        "sửa theo giờ UTC",
    )

    assert edited.work_date == date(2026, 4, 24)
    assert edited.check_in_at == dt(6, 0)
    assert edited.minutes == 120


@pytest.mark.unit
async def test_close_forgotten_accepts_utc_input(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(6, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(row)
    await session.flush()

    closed = await ReviewService(session, FakeClock(dt(20, 0))).close_forgotten(
        manager,
        row.id,
        utc_dt(1, 0),
        "đóng bằng giờ UTC",
    )

    assert closed.work_date == date(2026, 4, 24)
    assert closed.check_out_at == dt(8, 0)
    assert closed.minutes == 120


@pytest.mark.unit
async def test_close_forgotten_rejects_next_day_vn(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    row = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(18, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(row)
    await session.flush()

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).close_forgotten(manager, row.id, dt(0, 30, day=25), "qua ngày hôm sau")
    assert_code(exc, "INVALID_CHECKOUT_TIME")


@pytest.mark.unit
async def test_reason_required_for_close_and_edit(session):
    employee = await make_employee(session)
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    forgotten = WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(8, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.needs_review,
        review_reason="forgot_checkout",
        flags=[],
    )
    session.add(forgotten)
    editable = await closed_session(session, employee, dt(10, 0), dt(11, 0))
    await session.flush()

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).close_forgotten(manager, forgotten.id, dt(9, 0), "abc")
    assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).edit_session(manager, editable.id, dt(10, 0), dt(11, 30), "abc")
    assert_code(exc, "REASON_REQUIRED")


@pytest.mark.unit
async def test_api_rejects_naive_datetime(session):
    app = FastAPI()
    app.include_router(review_routes.router, prefix="/review")
    manager = EmployeeOrm(id=999, code="QL999", full_name="Quản lý", role=EmployeeRole.manager, is_active=True)

    async def override_manager():
        return manager

    async def override_session():
        yield session

    app.dependency_overrides[review_routes.manager_or_director] = override_manager
    app.dependency_overrides[review_routes.get_session] = override_session

    with TestClient(app) as client:
        response = client.patch(
            "/review/1",
            json={
                "check_in_time": "2026-04-24T08:00:00",
                "check_out_time": "2026-04-24T09:00:00+07:00",
                "reason": "sửa test",
            },
        )

    assert response.status_code == 422


@pytest.mark.unit
async def test_payroll_appendix_b_and_eligibility(session):
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    a = await make_employee(session, "NV001", "Nguyễn Văn A", 30_000)
    b = await make_employee(session, "NV002", "Lê Thị B", 28_000)
    d = await make_employee(session, "NV004", "Phạm Thị D", 28_000)
    day = date(2026, 4, 24)

    await closed_session(session, a, dt(6, 12), dt(11, 35), 30_000)
    batch1 = await PayrollService(session, FakeClock(dt(12, 0))).approve_one(manager, a.id, day)
    assert batch1.amount == 162_000

    await closed_session(session, a, dt(13, 5), dt(17, 10), 30_000)
    batch2 = await PayrollService(session, FakeClock(dt(17, 20))).approve_one(manager, a.id, day)
    assert batch2.amount == 122_000
    assert batch2.day_total_rounded_at_approval == 284_000

    await closed_session(session, b, dt(8, 0), dt(16, 0), 28_000)
    await closed_session(session, d, dt(9, 0), dt(15, 0), 28_000)
    batches = await PayrollService(session).approve(manager, [b.id, d.id], day)
    assert [batch.amount for batch in batches] == [224_000, 168_000]
    assert sum(batch.amount for batch in batches) == 392_000

    c = await make_employee(session, "NV003", "Trần Văn C", 30_000)
    await closed_session(session, c, dt(8, 0), dt(13, 5), 30_000)
    batch_c = await PayrollService(session).approve_one(manager, c.id, day)
    assert batch_c.amount == 153_000

    c_appendix = await make_employee(session, "NV006", "Trần Văn C phụ lục", 30_000)
    await closed_session(session, c_appendix, dt(8, 10), dt(15, 10), 30_000)
    batch_c_appendix = await PayrollService(session).approve_one(manager, c_appendix.id, day)
    assert batch_c_appendix.amount == 210_000

    flagged_employee = await make_employee(session, "NV005", "Có cờ GPS", 30_000)
    await closed_session(session, flagged_employee, dt(8, 0), dt(9, 0), 30_000, flags=["gps_out_of_range"])
    with pytest.raises(WorkforceError) as exc:
        await PayrollService(session).approve_one(manager, flagged_employee.id, day)
    assert_code(exc, "NO_ELIGIBLE_SESSIONS")

    with pytest.raises(WorkforceError) as exc:
        await PayrollService(session).approve(manager, [flagged_employee.id], day)
    assert_code(exc, "NO_ELIGIBLE_SESSIONS")


@pytest.mark.unit
async def test_payroll_open_session_does_not_block_and_listing(session):
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    employee = await make_employee(session)
    day = date(2026, 4, 24)
    await closed_session(session, employee, dt(8, 0), dt(9, 0), 30_000)
    session.add(WorkSessionOrm(
        employee_id=employee.id,
        work_date=day,
        check_in_at=dt(10, 0),
        check_in_lat=Decimal("10"),
        check_in_lng=Decimal("106"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("0"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    ))
    await session.flush()

    batch = await PayrollService(session).approve_one(manager, employee.id, day)
    assert batch.amount == 30_000

    listing = await PayrollService(session).list_payroll(day)
    row = next(item for item in listing if item["employee_id"] == employee.id)
    assert row["paid_amount"] == 30_000
    assert row["can_approve"] is False

    detail = await PayrollService(session).get_employee_payroll_detail(employee.id, day)
    assert detail["batches"][0]["amount"] == 30_000


@pytest.mark.unit
async def test_payroll_summary_distinguishes_no_sessions_gps_blocked_and_open(session):
    employee = await make_employee(session, "NV001")
    empty_employee = await make_employee(session, "NV002")
    first = await closed_session(session, employee, dt(7, 0), dt(8, 0), flags=["gps_out_of_range"])
    first.check_in_distance_m = Decimal("9")
    first.check_out_distance_m = Decimal("230")
    second = await closed_session(session, employee, dt(9, 0), dt(10, 0), flags=["gps_out_of_range"])
    second.check_in_distance_m = Decimal("9")
    second.check_out_distance_m = Decimal("180")
    session.add(WorkSessionOrm(
        employee_id=employee.id,
        work_date=date(2026, 4, 24),
        check_in_at=dt(11, 0),
        check_in_lat=Decimal("10.0"),
        check_in_lng=Decimal("106.0"),
        check_in_accuracy_m=Decimal("10"),
        check_in_distance_m=Decimal("9"),
        rate_snapshot=30_000,
        status=SessionStatus.open,
        flags=[],
    ))
    await session.flush()

    rows = await PayrollService(session, FakeClock(dt(17, 20))).list_payroll(date(2026, 4, 24))
    by_code = {row["code"]: row for row in rows}

    assert by_code["NV001"]["has_sessions"] is True
    assert by_code["NV001"]["pending_reason"] == "unreviewed_gps"
    assert by_code["NV001"]["pending_reasons"] == ["unreviewed_gps", "open_session"]
    assert by_code["NV001"]["blocked_amount"] == 60_000
    assert by_code["NV001"]["pending_amount"] == 0
    assert by_code["NV001"]["can_approve"] is False

    assert by_code["NV002"]["has_sessions"] is False
    assert by_code["NV002"]["pending_reason"] is None
    assert by_code["NV002"]["pending_reasons"] == []
    assert by_code["NV002"]["blocked_amount"] == 0


@pytest.mark.unit
async def test_history_day_includes_blocked_amount_and_session_flag_source(session):
    employee = await make_employee(session)
    row = await closed_session(session, employee, dt(7, 0), dt(10, 0), flags=["gps_out_of_range"])
    row.check_in_distance_m = Decimal("9")
    row.check_out_distance_m = Decimal("230")
    await session.flush()

    history = await HistoryService(session, FakeClock(dt(12))).history(employee, date(2026, 4, 24), date(2026, 4, 24))
    assert history["days"][0]["blocked_amount"] == 90_000
    payload = history["days"][0]["unpaid_sessions"][0]
    assert payload["flag_source"] == "check_out"
    assert payload["check_out_distance_m"] == 230.0


@pytest.mark.unit
async def test_session_dict_flag_source_check_out_distance(session):
    employee = await make_employee(session)
    row = await closed_session(session, employee, dt(7, 0), dt(8, 0), flags=["gps_out_of_range"])
    row.check_in_distance_m = Decimal("9")
    row.check_out_distance_m = Decimal("230")
    payload = session_dict(row)
    assert payload["flag_source"] == "check_out"


@pytest.mark.unit
async def test_payroll_zero_amount_batch_locks_sessions(session):
    manager = await make_employee(session, "QL001", "Quản lý", role=EmployeeRole.manager)
    employee = await make_employee(session, "NV001", "Nguyễn Văn A", 30_000)
    day = date(2026, 4, 24)

    await closed_session(session, employee, dt(6, 12), dt(11, 35), 30_000)
    batch1 = await PayrollService(session).approve_one(manager, employee.id, day)
    assert batch1.amount == 162_000

    one_minute = await closed_session(session, employee, dt(13, 0), dt(13, 1), 30_000)
    batch2 = await PayrollService(session).approve_one(manager, employee.id, day)

    assert batch2.batch_no == 2
    assert batch2.amount == 0
    assert batch2.day_total_rounded_at_approval == 162_000
    assert one_minute.pay_batch_id == batch2.id

    with pytest.raises(WorkforceError) as exc:
        await ReviewService(session).edit_session(manager, one_minute.id, dt(13, 0), dt(13, 2), "sửa sau khi trả")
    assert_code(exc, "SESSION_LOCKED_PAID")

    with pytest.raises(WorkforceError) as exc:
        await PayrollService(session).approve_one(manager, employee.id, day)
    assert_code(exc, "NO_ELIGIBLE_SESSIONS")


@pytest.mark.unit
async def test_batch_paid_zero_notification_text():
    row = NotificationOutboxOrm(
        dedupe_key="batch-paid:zero",
        chat_id=1,
        notification_type="batch_paid",
        payload={"batch_no": 2, "date": "2026-04-24", "amount": 0, "paid_total": 162_000},
    )

    text = notification_text(row)
    assert "<b>💰 ĐÃ DUYỆT LƯƠNG</b>" in text
    assert "🧾 Đợt: <b>2</b>" in text
    assert "(đã được làm tròn ở đợt trước)" in text
