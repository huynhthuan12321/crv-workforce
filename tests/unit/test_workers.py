from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from source.database.models import EmployeeOrm, NotificationOutboxOrm, PayBatchOrm, SyncOutboxOrm, WorkSessionOrm
from source.enums import EmployeeRole, OutboxStatus, SessionStatus
from source.services.workforce import PayrollService, ReviewService
from source.utils.clock import FakeClock, VIETNAM_TZ
import source.workers as workers_module
from source.workers import (
    escalate_job,
    notification_text,
    process_notifications,
    process_lark,
    reminder_job,
    run_startup_jobs,
    sweep_job,
)


NOW = datetime(2026, 4, 24, 18, 0, tzinfo=VIETNAM_TZ)


class FakeBot:
    def __init__(self, exc=None):
        self.exc = exc
        self.sent = []

    async def send_message(self, chat_id, text, reply_markup=None):
        if self.exc:
            raise self.exc
        self.sent.append((chat_id, text, reply_markup))


async def make_employee(session, code, role=EmployeeRole.employee, telegram_id=None):
    row = EmployeeOrm(code=code, full_name=code, role=role, telegram_id=telegram_id, is_active=True)
    session.add(row)
    await session.flush()
    return row


def make_session(employee_id, check_in, status=SessionStatus.open, check_out=None):
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
        check_out_lat=Decimal("10") if check_out else None,
        check_out_lng=Decimal("106") if check_out else None,
        check_out_accuracy_m=Decimal("10") if check_out else None,
        check_out_distance_m=Decimal("0") if check_out else None,
        rate_snapshot=30_000,
        minutes=minutes,
        amount_raw=Decimal(minutes or 0) * Decimal(30_000) / Decimal(60),
        status=status,
        flags=[],
    )


async def test_startup_sweep_notifies_manager_and_director_once(session_factory):
    yesterday = datetime(2026, 4, 23, 8, 12, tzinfo=VIETNAM_TZ)
    async with session_factory() as session, session.begin():
        employee = await make_employee(session, "NV001", telegram_id=1001)
        await make_employee(session, "QL001", EmployeeRole.manager, 2001)
        await make_employee(session, "GD001", EmployeeRole.director, 3001)
        session.add(make_session(employee.id, yesterday))

    clock = FakeClock(datetime(2026, 4, 24, 18, 5, tzinfo=VIETNAM_TZ))
    await run_startup_jobs(session_factory, clock)
    await run_startup_jobs(session_factory, clock)

    async with session_factory() as session:
        notices = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert len(notices) == 2
        assert all("NV001" in notification_text(row) for row in notices)
        row = await session.scalar(select(WorkSessionOrm))
        assert row.status == SessionStatus.needs_review


async def test_reminder_only_open_linked_employee_and_idempotent(session_factory):
    async with session_factory() as session, session.begin():
        open_emp = await make_employee(session, "OPEN", telegram_id=1001)
        closed_emp = await make_employee(session, "CLOSED", telegram_id=1002)
        unlinked_emp = await make_employee(session, "UNLINKED")
        session.add(make_session(open_emp.id, datetime(2026, 4, 24, 8, 12, tzinfo=VIETNAM_TZ)))
        session.add(make_session(closed_emp.id, datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ),
                                 SessionStatus.closed, datetime(2026, 4, 24, 9, 0, tzinfo=VIETNAM_TZ)))
        session.add(make_session(unlinked_emp.id, datetime(2026, 4, 24, 8, 30, tzinfo=VIETNAM_TZ)))

    clock = FakeClock(NOW)
    await reminder_job(session_factory, clock)
    await reminder_job(session_factory, clock)

    async with session_factory() as session:
        notices = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert len(notices) == 1
        assert notices[0].chat_id == 1001
        assert "08:12" in notification_text(notices[0])
        assert notices[0].payload["button"]["url"].endswith("tab_attendance")


async def test_escalate_1830_notifies_reviewers_with_session_list(session_factory):
    async with session_factory() as session, session.begin():
        employee = await make_employee(session, "NV1830", telegram_id=1001)
        await make_employee(session, "QL001", EmployeeRole.manager, 2001)
        await make_employee(session, "GD001", EmployeeRole.director, 3001)
        session.add(make_session(employee.id, datetime(2026, 4, 24, 8, 12, tzinfo=VIETNAM_TZ)))

    await escalate_job(session_factory, FakeClock(datetime(2026, 4, 24, 18, 30, tzinfo=VIETNAM_TZ)))
    await escalate_job(session_factory, FakeClock(datetime(2026, 4, 24, 18, 30, tzinfo=VIETNAM_TZ)))

    async with session_factory() as session:
        notices = list((await session.scalars(select(NotificationOutboxOrm))).all())
        assert len(notices) == 2
        assert all("NV1830" in notification_text(row) and "08:12" in notification_text(row) for row in notices)


async def test_close_forgotten_and_payroll_notification_texts(session_factory):
    async with session_factory() as session, session.begin():
        employee = await make_employee(session, "NVMSG", telegram_id=1001)
        manager = await make_employee(session, "QL001", EmployeeRole.manager, 2001)
        row = make_session(employee.id, datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ), SessionStatus.needs_review)
        row.review_reason = "forgot_checkout"
        session.add(row)
        await session.flush()
        row_id, manager_id, employee_id = row.id, manager.id, employee.id

    async with session_factory() as session, session.begin():
        manager = await session.get(EmployeeOrm, manager_id)
        await ReviewService(session, FakeClock(datetime(2026, 4, 24, 20, 0, tzinfo=VIETNAM_TZ))).close_forgotten(
            manager, row_id, datetime(2026, 4, 24, 17, 0, tzinfo=VIETNAM_TZ), "quen bam ra ca"
        )

    async with session_factory() as session:
        notice = await session.scalar(select(NotificationOutboxOrm).where(NotificationOutboxOrm.notification_type == "forgot_session_closed"))
        assert "24/04" in notification_text(notice)
        assert "20:00" in notification_text(notice)
        assert notice.payload["button"]["url"].endswith("tab_outputs")

    async with session_factory() as session, session.begin():
        # close_forgotten made a payable 540-minute session
        manager = await session.get(EmployeeOrm, manager_id)
        batch = await PayrollService(session, FakeClock(NOW)).approve_one(manager, employee_id, date(2026, 4, 24))
        assert isinstance(batch, PayBatchOrm)

    async with session_factory() as session:
        notice = await session.scalar(select(NotificationOutboxOrm).where(NotificationOutboxOrm.notification_type == "batch_paid"))
        assert "Đã duyệt lương đợt 1 ngày 24/04" in notification_text(notice)
        assert notice.payload["button"]["url"].endswith("tab_history")


async def test_process_notifications_403_failed_and_429_stops_batch(session_factory):
    workers_module._notifications_paused_until = None
    async with session_factory() as session, session.begin():
        session.add(NotificationOutboxOrm(dedupe_key="a", chat_id=1, notification_type="checkout_reminder",
                                          payload={"check_in": "08:00"}, status=OutboxStatus.pending))
    await process_notifications(FakeBot(TelegramForbiddenError(method=None, message="blocked")), session_factory, FakeClock(NOW))
    async with session_factory() as session:
        notice = await session.scalar(select(NotificationOutboxOrm))
        assert notice.status == OutboxStatus.failed
        assert notice.last_error == "bot_blocked"

    async with session_factory() as session, session.begin():
        session.add(NotificationOutboxOrm(dedupe_key="b", chat_id=2, notification_type="checkout_reminder",
                                          payload={"check_in": "08:00"}, status=OutboxStatus.pending))
        session.add(NotificationOutboxOrm(dedupe_key="c", chat_id=3, notification_type="checkout_reminder",
                                          payload={"check_in": "08:00"}, status=OutboxStatus.pending))
    await process_notifications(FakeBot(TelegramRetryAfter(method=None, message="retry", retry_after=30)), session_factory, FakeClock(NOW))
    async with session_factory() as session:
        row_b = await session.scalar(select(NotificationOutboxOrm).where(NotificationOutboxOrm.dedupe_key == "b"))
        row_c = await session.scalar(select(NotificationOutboxOrm).where(NotificationOutboxOrm.dedupe_key == "c"))
        assert row_b.next_attempt_at == (NOW + timedelta(seconds=30)).replace(tzinfo=None)
        assert row_c.next_attempt_at is None

    paused_bot = FakeBot()
    await process_notifications(paused_bot, session_factory, FakeClock(NOW + timedelta(seconds=5)))
    assert paused_bot.sent == []

    resumed_bot = FakeBot()
    await process_notifications(resumed_bot, session_factory, FakeClock(NOW + timedelta(seconds=31)))
    assert len(resumed_bot.sent) >= 1
    workers_module._notifications_paused_until = None


async def test_process_lark_sends_stable_event_id_and_outbox_id(session_factory, monkeypatch):
    sent = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            sent.append((url, content, headers))
            return FakeResponse()

    monkeypatch.setattr(workers_module.settings.lark, "sync_webhook_url", "https://n8n.local/webhook")
    monkeypatch.setattr(workers_module.httpx, "AsyncClient", FakeClient)
    async with session_factory() as session, session.begin():
        session.add(SyncOutboxOrm(event_type="session_closed", payload={"event_id": "evt-1", "session_id": 123}))

    await process_lark(session_factory, FakeClock(NOW))

    assert len(sent) == 1
    _, content, headers = sent[0]
    assert headers["X-CRV-Event-Id"] == "evt-1"
    assert b'"event_id":"evt-1"' in content
    assert b'"outbox_id":1' in content
