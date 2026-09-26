import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from source.config import settings
from source.database.models import (
    BotHeartbeatOrm, EmployeeOrm, NotificationOutboxOrm, SyncOutboxOrm, WorkSessionOrm,
)
from source.enums import EmployeeRole, OutboxStatus, SessionStatus
from source.services.workforce import ReviewService
from source.utils.clock import Clock, VIETNAM_TZ


def notification_text(row: NotificationOutboxOrm) -> str:
    p = row.payload
    if row.notification_type == "batch_paid" and int(p.get("amount", 0)) == 0:
        return f"Đợt {p.get('batch_no')}: 0đ (đã được làm tròn ở đợt trước)"
    messages = {
        "checkout_reminder": f"Bạn đang trong ca từ {p.get('check_in', '')}. Vui lòng bấm Ra ca nếu đã nghỉ.",
        "forgot_sessions": f"Có {p.get('count', 0)} phiên quên ra ca cần xử lý.",
        "forgot_session_closed": f"Phiên ngày {p.get('work_date')} đã được đóng. Bạn có 10 phút để khai sản lượng.",
        "batch_paid": f"Đã duyệt lương đợt {p.get('batch_no')} ngày {p.get('date')}: {p.get('amount', 0):,}đ. Tổng đã nhận hôm nay: {p.get('paid_total', 0):,}đ.".replace(",", "."),
        "consent_withdrawn": f"{p.get('employee_name')} đã rút lại đồng ý thu thập vị trí.",
    }
    return messages.get(row.notification_type, p.get("text", "Thông báo từ CRV Workforce"))


async def enqueue_if_missing(session: AsyncSession, **values) -> None:
    exists = await session.scalar(select(NotificationOutboxOrm.id).where(NotificationOutboxOrm.dedupe_key == values["dedupe_key"]))
    if not exists:
        session.add(NotificationOutboxOrm(**values))


async def reminder_job(factory: async_sessionmaker[AsyncSession]) -> None:
    now = Clock().now()
    async with factory() as session, session.begin():
        rows = (await session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.status == SessionStatus.open, WorkSessionOrm.work_date == now.date()))).all()
        for row in rows:
            employee = await session.get(EmployeeOrm, row.employee_id)
            if employee and employee.telegram_id:
                await enqueue_if_missing(session, dedupe_key=f"reminder:{now.date()}:{row.id}",
                    chat_id=employee.telegram_id, notification_type="checkout_reminder",
                    payload={"session_id": row.id, "check_in": row.check_in_at.strftime("%H:%M")})


async def _notify_reviewers(session: AsyncSession, key: str, count: int) -> None:
    reviewers = (await session.scalars(select(EmployeeOrm).where(
        EmployeeOrm.role.in_([EmployeeRole.manager, EmployeeRole.director]),
        EmployeeOrm.is_active.is_(True), EmployeeOrm.telegram_id.is_not(None)))).all()
    for reviewer in reviewers:
        await enqueue_if_missing(session, dedupe_key=f"{key}:{reviewer.id}", chat_id=reviewer.telegram_id,
            notification_type="forgot_sessions", payload={"count": count})


async def escalate_job(factory: async_sessionmaker[AsyncSession]) -> None:
    now = Clock().now()
    async with factory() as session, session.begin():
        rows = await ReviewService(session).escalate(now.date())
        if rows:
            await _notify_reviewers(session, f"escalate:{now.date()}", len(rows))


async def sweep_job(factory: async_sessionmaker[AsyncSession]) -> None:
    now = Clock().now()
    async with factory() as session, session.begin():
        rows = await ReviewService(session).sweep_stale()
        if rows:
            await _notify_reviewers(session, f"sweep:{now.date()}", len(rows))


async def worker_loop(bot: Bot, factory: async_sessionmaker[AsyncSession]) -> None:
    while True:
        try:
            await process_notifications(bot, factory)
            await process_lark(factory)
            async with factory() as session, session.begin():
                heartbeat = await session.get(BotHeartbeatOrm, 1)
                if heartbeat:
                    heartbeat.beat_at = Clock().now()
                else:
                    session.add(BotHeartbeatOrm(id=1, beat_at=Clock().now()))
        except Exception:
            logger.exception("Background worker iteration failed")
        await asyncio.sleep(30)


async def process_notifications(bot: Bot, factory: async_sessionmaker[AsyncSession]) -> None:
    now = Clock().now()
    async with factory() as session:
        rows = list((await session.scalars(select(NotificationOutboxOrm).where(
            NotificationOutboxOrm.status == OutboxStatus.pending,
            (NotificationOutboxOrm.next_attempt_at.is_(None) | (NotificationOutboxOrm.next_attempt_at <= now)),
        ).order_by(NotificationOutboxOrm.id).limit(50))).all())
        for row in rows:
            try:
                await bot.send_message(row.chat_id, notification_text(row))
                row.status, row.sent_at = OutboxStatus.sent, now
            except TelegramForbiddenError as exc:
                row.status, row.last_error = OutboxStatus.failed, "bot_blocked"
            except TelegramRetryAfter as exc:
                row.next_attempt_at = now + timedelta(seconds=exc.retry_after)
            except Exception as exc:
                row.attempts += 1
                row.last_error = type(exc).__name__
                if row.attempts >= 10:
                    row.status = OutboxStatus.failed
                else:
                    row.next_attempt_at = now + timedelta(seconds=min(3600, 2 ** row.attempts * 10))
        await session.commit()


async def process_lark(factory: async_sessionmaker[AsyncSession]) -> None:
    if not settings.lark.sync_webhook_url:
        return
    now = Clock().now()
    async with factory() as session:
        rows = list((await session.scalars(select(SyncOutboxOrm).where(
            SyncOutboxOrm.status == OutboxStatus.pending,
            (SyncOutboxOrm.next_attempt_at.is_(None) | (SyncOutboxOrm.next_attempt_at <= now)),
        ).order_by(SyncOutboxOrm.id).limit(50))).all())
        async with httpx.AsyncClient(timeout=15) as client:
            for row in rows:
                body = json.dumps({"event_type": row.event_type, **row.payload}, ensure_ascii=False, separators=(",", ":")).encode()
                signature = hmac.new(settings.lark.sync_secret.get_secret_value().encode(), body, hashlib.sha256).hexdigest()
                try:
                    response = await client.post(settings.lark.sync_webhook_url, content=body,
                        headers={"Content-Type": "application/json", "X-CRV-Signature": signature})
                    response.raise_for_status()
                    row.status, row.sent_at = OutboxStatus.sent, now
                except Exception as exc:
                    row.attempts += 1
                    row.last_error = type(exc).__name__
                    row.status = OutboxStatus.failed if row.attempts >= 10 else OutboxStatus.pending
                    row.next_attempt_at = now + timedelta(seconds=min(3600, 2 ** row.attempts * 10))
        await session.commit()


def build_scheduler(factory: async_sessionmaker[AsyncSession]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=VIETNAM_TZ)
    for fn, value, job_id in [
        (reminder_job, settings.rules.reminder_at, "reminder"),
        (escalate_job, settings.rules.escalate_at, "escalate"),
        (sweep_job, settings.rules.sweep_at, "sweep"),
    ]:
        scheduler.add_job(fn, "cron", hour=value.hour, minute=value.minute,
                          args=[factory], id=job_id, replace_existing=True,
                          misfire_grace_time=3600, coalesce=True, max_instances=1)
    return scheduler
