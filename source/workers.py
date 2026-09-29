import asyncio
import hashlib
import hmac
import json
import os
import re
from datetime import timedelta
from html import unescape
from time import monotonic

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from source.config import settings
from source.database.models import (
    BotHeartbeatOrm, EmployeeOrm, NotificationOutboxOrm, SyncOutboxOrm, WorkSessionOrm,
)
from source.enums import EmployeeRole, OutboxStatus, SessionStatus
from source.services.workforce import ReviewService
from source.telegram.messages import render_notification
from source.utils.clock import Clock, VIETNAM_TZ
from source.utils.formatting import fmt_date_vn, fmt_time_vn

_notifications_paused_until = None


def _elapsed_minutes(now, started_at) -> int:
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        started_at = started_at.replace(tzinfo=VIETNAM_TZ)
    return max(0, int((now - started_at.astimezone(VIETNAM_TZ)).total_seconds() // 60))


def app_tab_link(tab: str) -> str:
    return f"https://t.me/{settings.tg.bot_username}/{settings.tg.miniapp_short_name}?startapp=tab_{tab}"


def button_payload(text: str, tab: str) -> dict:
    return {"text": text, "url": app_tab_link(tab)}


def notification_markup(row: NotificationOutboxOrm) -> InlineKeyboardMarkup | None:
    tabs = {
        "batch_paid": ("📋 Xem chi tiết", "history"),
        "checkout_reminder": ("🔴 Ra ca ngay", "attendance"),
        "forgot_sessions": ("🛠 Xử lý ngay", "review"),
        "forgot_session_closed": ("📦 Khai sản lượng", "outputs"),
        "rate_changed": ("📱 Mở ứng dụng", "attendance"),
        "rate_scheduled": ("📱 Mở ứng dụng", "attendance"),
        "rate_cancelled": ("📱 Mở ứng dụng", "attendance"),
    }
    button = tabs.get(row.notification_type)
    if not button:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button[0], url=app_tab_link(button[1]))
    ]])


def notification_reply_markup(row: NotificationOutboxOrm) -> InlineKeyboardMarkup | ReplyKeyboardRemove | None:
    if row.notification_type == "account_locked":
        return ReplyKeyboardRemove()
    return notification_markup(row)


def notification_text(row: NotificationOutboxOrm) -> str:
    return render_notification(row.notification_type, row.payload or {})


def _plain_notification_text(value: str) -> str:
    """Remove Telegram HTML tags while preserving escaped user content."""
    return unescape(re.sub(r"</?(?:b|strong|s|i|u|code|pre|a)(?:\s[^>]*)?>", "", value, flags=re.IGNORECASE))


async def enqueue_if_missing(session: AsyncSession, **values) -> None:
    exists = await session.scalar(select(NotificationOutboxOrm.id).where(NotificationOutboxOrm.dedupe_key == values["dedupe_key"]))
    if not exists:
        session.add(NotificationOutboxOrm(**values))


async def reminder_job(factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    clock = clock or Clock()
    now = clock.now()
    async with factory() as session, session.begin():
        rows = (await session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.status == SessionStatus.open, WorkSessionOrm.work_date == now.date()))).all()
        for row in rows:
            employee = await session.get(EmployeeOrm, row.employee_id)
            if employee and employee.telegram_id:
                minutes = _elapsed_minutes(now, row.check_in_at)
                await enqueue_if_missing(session, dedupe_key=f"reminder:{now.date()}:{row.id}",
                    chat_id=employee.telegram_id, notification_type="checkout_reminder",
                    payload={"session_id": row.id, "check_in": fmt_time_vn(row.check_in_at),
                             "minutes": minutes, "location_code": row.location_code_snapshot,
                             "location_name": row.location_name_snapshot,
                             "button": button_payload("Mở ứng dụng", "attendance")})


async def _session_payloads(session: AsyncSession, rows: list[WorkSessionOrm]) -> list[dict]:
    result = []
    for row in rows:
        employee = await session.get(EmployeeOrm, row.employee_id)
        result.append({
            "session_id": row.id,
            "employee_name": employee.full_name if employee else str(row.employee_id),
            "employee_code": employee.code if employee else "",
            "date": fmt_date_vn(row.check_in_at),
            "check_in": fmt_time_vn(row.check_in_at),
            "location_code": row.location_code_snapshot,
            "location_name": row.location_name_snapshot,
        })
    return result


async def _notify_reviewers(session: AsyncSession, key: str, rows: list[WorkSessionOrm]) -> None:
    reviewers = (await session.scalars(select(EmployeeOrm).where(
        EmployeeOrm.role.in_([EmployeeRole.manager, EmployeeRole.director]),
        EmployeeOrm.is_active.is_(True), EmployeeOrm.telegram_id.is_not(None)))).all()
    sessions = await _session_payloads(session, rows)
    for reviewer in reviewers:
        await enqueue_if_missing(session, dedupe_key=f"{key}:{reviewer.id}", chat_id=reviewer.telegram_id,
            notification_type="forgot_sessions", payload={"count": len(rows), "sessions": sessions,
                                                          "button": button_payload("Mở ứng dụng", "review")})


async def escalate_job(factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    clock = clock or Clock()
    now = clock.now()
    async with factory() as session, session.begin():
        rows = await ReviewService(session, clock).escalate(now.date())
        if rows:
            await _notify_reviewers(session, f"escalate:{now.date()}", rows)


async def sweep_job(factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    clock = clock or Clock()
    now = clock.now()
    async with factory() as session, session.begin():
        rows = await ReviewService(session, clock).sweep_stale()
        if rows:
            await _notify_reviewers(session, f"sweep:{now.date()}", rows)


async def run_startup_jobs(factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    clock = clock or Clock()
    now = clock.now()
    await sweep_job(factory, clock)
    if settings.rules.reminder_at <= now.time() < settings.rules.escalate_at:
        await reminder_job(factory, clock)
    elif now.time() >= settings.rules.escalate_at:
        await escalate_job(factory, clock)


async def _check_lock_connection(lock_conn: AsyncConnection | None) -> None:
    if lock_conn is None:
        return
    await lock_conn.scalar(text("SELECT 1"))


async def worker_loop(
    bot: Bot,
    factory: async_sessionmaker[AsyncSession],
    clock: Clock | None = None,
    lock_conn: AsyncConnection | None = None,
) -> None:
    clock = clock or Clock()
    last_lock_check = 0.0
    while True:
        try:
            now_monotonic = monotonic()
            if now_monotonic - last_lock_check >= 60:
                last_lock_check = now_monotonic
                try:
                    await _check_lock_connection(lock_conn)
                except Exception:
                    logger.error("Bot advisory lock connection is lost; stopping process for restart")
                    os._exit(1)
            await process_notifications(bot, factory, clock)
            await process_lark(factory, clock)
            async with factory() as session, session.begin():
                heartbeat = await session.get(BotHeartbeatOrm, 1)
                if heartbeat:
                    heartbeat.beat_at = clock.now()
                else:
                    session.add(BotHeartbeatOrm(id=1, beat_at=clock.now()))
        except Exception:
            logger.exception("Background worker iteration failed")
        await asyncio.sleep(5)


async def process_notifications(bot: Bot, factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    global _notifications_paused_until
    now = (clock or Clock()).now()
    if _notifications_paused_until is not None and now < _notifications_paused_until:
        return
    if _notifications_paused_until is not None and now >= _notifications_paused_until:
        _notifications_paused_until = None
    async with factory() as session:
        rows = list((await session.scalars(select(NotificationOutboxOrm).where(
            NotificationOutboxOrm.status == OutboxStatus.pending,
            (NotificationOutboxOrm.next_attempt_at.is_(None) | (NotificationOutboxOrm.next_attempt_at <= now)),
        ).order_by(NotificationOutboxOrm.id).limit(50))).all())
        for row in rows:
            try:
                text_value = notification_text(row)
                await bot.send_message(row.chat_id, text_value, reply_markup=notification_reply_markup(row))
                row.status, row.sent_at = OutboxStatus.sent, now
            except TelegramForbiddenError:
                row.status, row.last_error = OutboxStatus.failed, "bot_blocked"
            except TelegramRetryAfter as exc:
                _notifications_paused_until = now + timedelta(seconds=exc.retry_after)
                row.next_attempt_at = _notifications_paused_until
                await session.commit()
                return
            except TelegramBadRequest as exc:
                if "can't parse entities" not in str(exc).lower():
                    row.attempts += 1
                    row.last_error = type(exc).__name__
                    if row.attempts >= 10:
                        row.status = OutboxStatus.failed
                    else:
                        row.next_attempt_at = now + timedelta(seconds=min(3600, 2 ** row.attempts * 10))
                    await session.commit()
                    continue
                logger.warning(
                    "Telegram HTML parse fallback notification_type={} notification_id={}",
                    row.notification_type,
                    row.id,
                )
                try:
                    await bot.send_message(
                        row.chat_id,
                        _plain_notification_text(notification_text(row)),
                        reply_markup=notification_reply_markup(row),
                    )
                    row.status, row.sent_at = OutboxStatus.sent, now
                    row.last_error = "html_parse_fallback"
                except Exception as fallback_exc:
                    row.status = OutboxStatus.failed
                    row.last_error = type(fallback_exc).__name__
            except Exception as exc:
                row.attempts += 1
                row.last_error = type(exc).__name__
                if row.attempts >= 10:
                    row.status = OutboxStatus.failed
                else:
                    row.next_attempt_at = now + timedelta(seconds=min(3600, 2 ** row.attempts * 10))
            await session.commit()


async def process_lark(factory: async_sessionmaker[AsyncSession], clock: Clock | None = None) -> None:
    if not settings.lark.sync_webhook_url:
        return
    now = (clock or Clock()).now()
    async with factory() as session:
        rows = list((await session.scalars(select(SyncOutboxOrm).where(
            SyncOutboxOrm.status == OutboxStatus.pending,
            (SyncOutboxOrm.next_attempt_at.is_(None) | (SyncOutboxOrm.next_attempt_at <= now)),
        ).order_by(SyncOutboxOrm.id).limit(50))).all())
        async with httpx.AsyncClient(timeout=15) as client:
            for row in rows:
                event_id = (row.payload or {}).get("event_id", "")
                body = json.dumps({"outbox_id": row.id, "event_type": row.event_type, **row.payload}, ensure_ascii=False, separators=(",", ":")).encode()
                signature = hmac.new(settings.lark.sync_secret.get_secret_value().encode(), body, hashlib.sha256).hexdigest()
                try:
                    response = await client.post(settings.lark.sync_webhook_url, content=body,
                        headers={"Content-Type": "application/json", "X-CRV-Signature": signature,
                                 "X-CRV-Event-Id": str(event_id)})
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
