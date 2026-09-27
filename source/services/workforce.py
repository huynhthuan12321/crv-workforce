import math
import secrets
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from source.config import settings
from source.database.models import (
    AuditLogOrm, ConsentTextOrm, EmployeeOrm, InviteCodeOrm,
    LocationConsentOrm, NotificationOutboxOrm, OutputItemOrm, OutputLogOrm,
    PayBatchOrm, ProductOrm, RateHistoryOrm, SyncOutboxOrm, WorkSessionOrm,
)
from source.domain.workforce_errors import fail
from source.enums import EmployeeRole, SessionStatus
from source.utils.clock import Clock, VIETNAM_TZ, to_vn
from source.utils.formatting import fmt_date_vn, fmt_time_vn, iso_vn


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def ceil_money(value: Decimal, unit: int | None = None) -> int:
    unit = unit or settings.rules.pay_round_unit
    return int((value / Decimal(unit)).to_integral_value(rounding=ROUND_CEILING) * unit)


def _flags(distance: float, accuracy: float) -> list[str]:
    result = []
    if distance > settings.workshop.radius_m:
        result.append("gps_out_of_range")
    if accuracy > settings.rules.gps_max_accuracy_m:
        result.append("gps_low_accuracy")
    return result


def _event(event_type: str, payload: dict) -> SyncOutboxOrm:
    return SyncOutboxOrm(event_type=event_type, payload={"event_id": str(uuid.uuid4()), **payload})


def _notice(key: str, chat_id: int | None, kind: str, payload: dict) -> NotificationOutboxOrm | None:
    if not chat_id:
        return None
    return NotificationOutboxOrm(dedupe_key=key, chat_id=chat_id, notification_type=kind, payload=payload)


def invite_url(code: str) -> str:
    return f"https://t.me/{settings.tg.bot_username}/{settings.tg.miniapp_short_name}?startapp={code}"


def _tab_button(text: str, tab: str) -> dict:
    return {"text": text, "url": f"https://t.me/{settings.tg.bot_username}/{settings.tg.miniapp_short_name}?startapp=tab_{tab}"}


def _has_unreviewed_flags(row: WorkSessionOrm) -> bool:
    return bool(row.flags) and row.flags_reviewed_at is None


def _review_type(row: WorkSessionOrm) -> str | None:
    if row.status == SessionStatus.needs_review or row.review_reason == "forgot_checkout":
        return "forgot"
    if _has_unreviewed_flags(row):
        return "gps"
    return None


def _vn(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=VIETNAM_TZ)
    return value.astimezone(VIETNAM_TZ)


def _recalculate_session(row: WorkSessionOrm) -> None:
    if row.check_out_at is None:
        row.minutes = None
        row.amount_raw = None
        return
    row.minutes = max(0, int((_vn(row.check_out_at) - _vn(row.check_in_at)).total_seconds() // 60))
    row.amount_raw = Decimal(row.minutes) * Decimal(row.rate_snapshot) / Decimal(60)


async def current_consent(session: AsyncSession, employee_id: int, now: datetime) -> tuple[ConsentTextOrm | None, bool]:
    text_row = await session.scalar(select(ConsentTextOrm).where(ConsentTextOrm.effective_at <= now).order_by(ConsentTextOrm.effective_at.desc()).limit(1))
    if not text_row:
        return None, False
    consent = await session.scalar(select(LocationConsentOrm).where(
        LocationConsentOrm.employee_id == employee_id,
        LocationConsentOrm.consent_version == text_row.version,
        LocationConsentOrm.withdrawn_at.is_(None),
    ).order_by(LocationConsentOrm.consented_at.desc()).limit(1))
    return text_row, consent is not None


async def employee_payload(session: AsyncSession, employee: EmployeeOrm, now: datetime | None = None) -> dict:
    tabs = {
        "employee": ["attendance", "outputs", "history"],
        "manager": ["working", "review", "payroll", "employees"],
        "director": ["reports", "review", "payroll"],
    }[employee.role.value]
    _, accepted = await current_consent(session, employee.id, now or Clock().now())
    return {"id": employee.id, "code": employee.code, "full_name": employee.full_name,
            "role": employee.role.value, "tabs": tabs, "has_location_consent": accepted}


async def create_invite(session: AsyncSession, employee: EmployeeOrm, actor_id: int | None, now: datetime | None = None) -> str:
    now = now or Clock().now()
    rows = (await session.scalars(select(InviteCodeOrm).where(
        InviteCodeOrm.employee_id == employee.id,
        InviteCodeOrm.used_at.is_(None),
        InviteCodeOrm.expires_at > now,
    ).with_for_update())).all()
    for row in rows:
        row.expires_at = now
    code_value = secrets.token_urlsafe(32)
    session.add(InviteCodeOrm(employee_id=employee.id, code=code_value, created_by=actor_id,
                              expires_at=now + timedelta(days=settings.rules.invite_expire_days)))
    return invite_url(code_value)


async def current_hourly_rate(session: AsyncSession, employee_id: int, day: date | None = None) -> int | None:
    day = day or _vn(Clock().now()).date()
    return await session.scalar(select(RateHistoryOrm.hourly_rate).where(
        RateHistoryOrm.employee_id == employee_id,
        RateHistoryOrm.effective_from <= day,
    ).order_by(RateHistoryOrm.effective_from.desc()).limit(1))


async def has_open_session(session: AsyncSession, employee_id: int) -> bool:
    opened = await session.scalar(select(WorkSessionOrm.id).where(
        WorkSessionOrm.employee_id == employee_id,
        WorkSessionOrm.status == SessionStatus.open,
    ).limit(1))
    return opened is not None


async def employee_admin_dict(session: AsyncSession, row: EmployeeOrm, day: date | None = None) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "full_name": row.full_name,
        "role": row.role.value,
        "telegram_id": row.telegram_id,
        "is_active": row.is_active,
        "current_hourly_rate": await current_hourly_rate(session, row.id, day),
        "is_linked": row.telegram_id is not None,
        "has_open_session": await has_open_session(session, row.id),
    }


class AuthService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session = session
        self.clock = clock or Clock()

    async def redeem_invite(self, data: dict) -> EmployeeOrm:
        code = data.get("start_param")
        if not code:
            raise fail("INVITE_INVALID", 422)
        now = self.clock.now()
        telegram_id = int(data["user"]["id"])
        invite = await self.session.scalar(select(InviteCodeOrm).where(InviteCodeOrm.code == code).with_for_update())
        if not invite:
            raise fail("INVITE_INVALID", 422)
        employee = await self.session.get(EmployeeOrm, invite.employee_id)
        if not employee or not employee.is_active:
            raise fail("ACCOUNT_LOCKED", 403)
        if employee.telegram_id == telegram_id:
            return employee
        already = await self.session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == telegram_id))
        if already:
            raise fail("TELEGRAM_ALREADY_LINKED")
        if invite.used_at:
            raise fail("INVITE_USED")
        expires_at = _vn(invite.expires_at)
        if expires_at <= now:
            raise fail("INVITE_EXPIRED")
        employee.telegram_id = telegram_id
        employee.telegram_username = data["user"].get("username")
        invite.used_at = now
        self.session.add(AuditLogOrm(actor_id=None, action="employee_linked",
                                     entity_type="employee", entity_id=employee.id))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise fail("TELEGRAM_ALREADY_LINKED") from exc
        return employee


class ConsentService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session = session
        self.clock = clock or Clock()

    async def withdraw(self, employee: EmployeeOrm) -> None:
        now = self.clock.now()
        text, accepted = await current_consent(self.session, employee.id, now)
        if text and accepted:
            row = await self.session.scalar(select(LocationConsentOrm).where(
                LocationConsentOrm.employee_id == employee.id,
                LocationConsentOrm.consent_version == text.version,
                LocationConsentOrm.withdrawn_at.is_(None)).order_by(LocationConsentOrm.id.desc()).limit(1))
            if row:
                row.withdrawn_at = now
        managers = (await self.session.scalars(select(EmployeeOrm).where(
            EmployeeOrm.role == EmployeeRole.manager, EmployeeOrm.is_active.is_(True),
            EmployeeOrm.telegram_id.is_not(None)))).all()
        for manager in managers:
            self.session.add(NotificationOutboxOrm(
                dedupe_key=f"consent-withdrawn:{employee.id}:{manager.id}:{int(now.timestamp())}",
                chat_id=manager.telegram_id, notification_type="consent_withdrawn",
                payload={"employee_id": employee.id, "employee_name": employee.full_name}))


class AttendanceService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session = session
        self.clock = clock or Clock()

    async def _rate(self, employee_id: int, day: date) -> int:
        rate = await self.session.scalar(select(RateHistoryOrm.hourly_rate).where(
            RateHistoryOrm.employee_id == employee_id,
            RateHistoryOrm.effective_from <= day,
        ).order_by(RateHistoryOrm.effective_from.desc()).limit(1))
        if rate is None:
            raise fail("NO_RATE")
        return rate

    async def check_in(self, employee: EmployeeOrm, lat: float, lng: float, accuracy_m: float) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        _, consented = await current_consent(self.session, employee.id, now)
        if not consented:
            raise fail("LOCATION_CONSENT_REQUIRED")
        if now.time() >= settings.rules.checkin_cutoff:
            raise fail("CHECKIN_AFTER_CUTOFF")
        opened = await self.session.scalar(select(WorkSessionOrm.id).where(
            WorkSessionOrm.employee_id == employee.id, WorkSessionOrm.status == SessionStatus.open))
        if opened:
            raise fail("SESSION_ALREADY_OPEN")
        distance = haversine_m(lat, lng, settings.workshop.lat, settings.workshop.lng)
        row = WorkSessionOrm(
            employee_id=employee.id, work_date=now.date(), check_in_at=now,
            check_in_lat=Decimal(str(lat)), check_in_lng=Decimal(str(lng)),
            check_in_accuracy_m=Decimal(str(accuracy_m)), check_in_distance_m=Decimal(str(distance)),
            rate_snapshot=await self._rate(employee.id, now.date()),
            status=SessionStatus.open, flags=_flags(distance, accuracy_m),
        )
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise fail("SESSION_ALREADY_OPEN") from exc
        return row

    async def check_out(self, employee: EmployeeOrm, lat: float, lng: float, accuracy_m: float) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        row = await self.session.scalar(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee.id,
            WorkSessionOrm.status == SessionStatus.open,
        ).with_for_update())
        if not row:
            raise fail("NO_OPEN_SESSION")
        distance = haversine_m(lat, lng, settings.workshop.lat, settings.workshop.lng)
        row.check_out_at = now
        row.check_out_lat, row.check_out_lng = Decimal(str(lat)), Decimal(str(lng))
        row.check_out_accuracy_m, row.check_out_distance_m = Decimal(str(accuracy_m)), Decimal(str(distance))
        row.flags = list(dict.fromkeys([*(row.flags or []), *_flags(distance, accuracy_m)]))
        row.minutes = max(0, int((now - _vn(row.check_in_at)).total_seconds() // 60))
        row.amount_raw = Decimal(row.minutes) * Decimal(row.rate_snapshot) / Decimal(60)
        row.status, row.closed_by = SessionStatus.closed, employee.id
        self.session.add(OutputLogOrm(work_session_id=row.id, locked_at=now + timedelta(minutes=settings.rules.output_edit_minutes)))
        self.session.add(_event("session_closed", {"session_id": row.id, "employee_id": employee.id}))
        await self.session.flush()
        return row

    async def today(self, employee: EmployeeOrm) -> dict:
        now = _vn(self.clock.now())
        rows = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee.id, WorkSessionOrm.work_date == now.date()))).all())
        opened = next((x for x in rows if x.status == SessionStatus.open), None)
        raw = sum((x.amount_raw or Decimal(0) for x in rows if x.status == SessionStatus.closed), Decimal(0))
        if opened:
            running_minutes = max(0, int((now - _vn(opened.check_in_at)).total_seconds() // 60))
            raw += Decimal(running_minutes) * Decimal(opened.rate_snapshot) / Decimal(60)
        paid = await self.session.scalar(select(func.coalesce(func.sum(PayBatchOrm.amount), 0)).where(
            PayBatchOrm.employee_id == employee.id, PayBatchOrm.work_date == now.date()))
        return {"open_session": session_dict(opened) if opened else None,
                "estimated_day_amount": ceil_money(raw), "paid_today": int(paid or 0)}


class WorkingService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def working_now(self) -> list[dict]:
        now = _vn(self.clock.now())
        rows = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.status == SessionStatus.open,
            WorkSessionOrm.work_date == now.date(),
        ).order_by(WorkSessionOrm.check_in_at))).all())
        result = []
        for row in rows:
            employee = await self.session.get(EmployeeOrm, row.employee_id)
            check_in = _vn(row.check_in_at)
            result.append({
                "session_id": row.id,
                "employee_id": row.employee_id,
                "code": employee.code if employee else "",
                "full_name": employee.full_name if employee else "",
                "check_in_at": iso_vn(row.check_in_at),
                "minutes_worked": max(0, int((now - check_in).total_seconds() // 60)),
                "flags": row.flags or [],
                "check_in_distance_m": float(row.check_in_distance_m) if row.check_in_distance_m is not None else None,
                "check_in_accuracy_m": float(row.check_in_accuracy_m) if row.check_in_accuracy_m is not None else None,
                "is_outside": "gps_out_of_range" in (row.flags or []),
            })
        return result


class OutputService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def form(self, employee: EmployeeOrm, session_id: int) -> dict:
        work = await self.session.get(WorkSessionOrm, session_id)
        if not work or work.employee_id != employee.id:
            raise fail("NOT_OWNER", 403)
        output = await self.session.scalar(select(OutputLogOrm).where(OutputLogOrm.work_session_id == session_id))
        if not output:
            raise fail("SESSION_NOT_CLOSED")
        products = list((await self.session.scalars(select(ProductOrm).order_by(ProductOrm.sort_order))).all())
        items = {x.product_id: x for x in (await self.session.scalars(select(OutputItemOrm).where(OutputItemOrm.output_log_id == output.id))).all()}
        now = _vn(self.clock.now())
        locked_at = _vn(output.locked_at)
        return {"session_id": session_id, "locked": now >= locked_at,
                "seconds_remaining": max(0, int((locked_at - now).total_seconds())),
                "locked_at": iso_vn(output.locked_at),
                "items": [{"code": p.code, "name": p.name, "kg_per_bag": float(p.kg_per_bag),
                           "bags": items[p.id].bags if p.id in items else 0} for p in products]}

    async def submit(self, employee: EmployeeOrm, session_id: int, values: dict[str, int]) -> dict:
        work = await self.session.get(WorkSessionOrm, session_id)
        if not work or work.employee_id != employee.id:
            raise fail("NOT_OWNER", 403)
        output = await self.session.scalar(select(OutputLogOrm).where(OutputLogOrm.work_session_id == session_id).with_for_update())
        now = _vn(self.clock.now())
        if not output or work.status != SessionStatus.closed:
            raise fail("SESSION_NOT_CLOSED")
        if now >= _vn(output.locked_at):
            raise fail("OUTPUT_LOCKED")
        products = list((await self.session.scalars(select(ProductOrm))).all())
        known = {p.code for p in products}
        if set(values) - known or any(not isinstance(v, int) or v < 0 or v > 9999 for v in values.values()):
            raise fail("OUTPUT_INVALID", 422)
        await self.session.execute(delete(OutputItemOrm).where(OutputItemOrm.output_log_id == output.id))
        total = Decimal(0)
        for product in products:
            bags = values.get(product.code, 0)
            kg = Decimal(bags) * product.kg_per_bag
            total += kg
            self.session.add(OutputItemOrm(output_log_id=output.id, product_id=product.id, bags=bags, kg=kg))
        output.submitted_at = now
        self.session.add(_event("output_submitted", {"session_id": session_id, "items": values}))
        await self.session.flush()
        return {"session_id": session_id, "total_kg": float(total), "locked_at": iso_vn(output.locked_at)}


class ReviewService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def _review_item(self, row: WorkSessionOrm) -> dict:
        employee = await self.session.get(EmployeeOrm, row.employee_id)
        return session_dict(row) | {
            "employee_code": employee.code if employee else "",
            "employee_name": employee.full_name if employee else "",
            "review_reason": row.review_reason,
        }

    async def _handled_details(self, row: WorkSessionOrm | None) -> dict:
        if not row:
            return {}
        actor_id = row.flags_reviewed_by or row.closed_by
        actor = await self.session.get(EmployeeOrm, actor_id) if actor_id else None
        handled_at = row.flags_reviewed_at or row.updated_at
        return {
            "handled_by_name": actor.full_name if actor else None,
            "handled_at": iso_vn(handled_at) if handled_at else None,
            "action": "flags_reviewed" if row.flags_reviewed_at else "session_closed",
        }

    async def pending(self, type_: str | None = None) -> list[dict]:
        rows = (await self.session.scalars(select(WorkSessionOrm).where(or_(
            WorkSessionOrm.status == SessionStatus.needs_review,
            WorkSessionOrm.status == SessionStatus.closed,
        )).order_by(WorkSessionOrm.check_in_at))).all()
        result = []
        for row in rows:
            row_type = _review_type(row)
            if not row_type or (type_ and row_type != type_):
                continue
            result.append(await self._review_item(row))
        return result

    async def mark_flags(self, actor: EmployeeOrm, session_id: int) -> WorkSessionOrm:
        row = await self.session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update())
        if not row or row.flags_reviewed_at:
            raise fail("ALREADY_HANDLED", details=await self._handled_details(row))
        row.flags_reviewed_by, row.flags_reviewed_at = actor.id, _vn(self.clock.now())
        self.session.add(AuditLogOrm(actor_id=actor.id, action="flags_reviewed", entity_type="work_session", entity_id=row.id))
        return row

    async def list_resolved(self, type_: str | None = None) -> list[dict]:
        rows = (await self.session.scalars(select(WorkSessionOrm).where(or_(
            WorkSessionOrm.flags_reviewed_at.is_not(None),
            WorkSessionOrm.closed_by.is_not(None),
        )).order_by(WorkSessionOrm.updated_at.desc()))).all()
        resolved = []
        for row in rows:
            row_type = "gps" if row.flags_reviewed_at else "forgot"
            if type_ and row_type != type_:
                continue
            resolved_by = row.flags_reviewed_by or row.closed_by
            actor = await self.session.get(EmployeeOrm, resolved_by) if resolved_by else None
            data = await self._review_item(row)
            data.update({
                "resolved_by": resolved_by,
                "resolved_by_name": actor.full_name if actor else None,
                "resolved_at": iso_vn(row.flags_reviewed_at or row.updated_at),
                "resolved_action": "flags_reviewed" if row.flags_reviewed_at else "session_closed",
                "reason": row.review_reason,
            })
            resolved.append(data)
        return resolved

    async def close_forgotten(self, actor: EmployeeOrm, session_id: int, check_out: datetime, reason: str) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        check_out_vn = to_vn(check_out)
        row = await self.session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update())
        if not row or row.status != SessionStatus.needs_review:
            raise fail("ALREADY_HANDLED", details=await self._handled_details(row))
        if len(reason.strip()) < 5 or len(reason) > 200:
            raise fail("REASON_REQUIRED", 422)
        check_in_vn = _vn(row.check_in_at)
        if check_out_vn <= check_in_vn or check_out_vn.date() != row.work_date:
            raise fail("INVALID_CHECKOUT_TIME", 422)
        row.check_out_at = check_out_vn
        _recalculate_session(row)
        row.status, row.closed_by = SessionStatus.closed, actor.id
        self.session.add(OutputLogOrm(work_session_id=row.id, locked_at=now + timedelta(minutes=settings.rules.output_edit_minutes)))
        self.session.add(AuditLogOrm(actor_id=actor.id, action="session_close_by_manager", entity_type="work_session", entity_id=row.id, reason=reason))
        self.session.add(_event("session_closed", {"session_id": row.id, "employee_id": row.employee_id}))
        employee = await self.session.get(EmployeeOrm, row.employee_id)
        notice = _notice(f"forgot-closed:{row.id}", employee.telegram_id if employee else None,
                         "forgot_session_closed", {"session_id": row.id,
                                                   "work_date": fmt_date_vn(row.work_date),
                                                   "closed_at": iso_vn(now),
                                                   "closed_time": fmt_time_vn(now),
                                                   "button": _tab_button("Mở ứng dụng", "outputs")})
        if notice:
            self.session.add(notice)
        await self.session.flush()
        return row

    async def edit_session(
        self,
        actor: EmployeeOrm,
        session_id: int,
        new_check_in: datetime,
        new_check_out: datetime,
        reason: str,
    ) -> WorkSessionOrm:
        new_check_in_vn = to_vn(new_check_in)
        new_check_out_vn = to_vn(new_check_out)
        row = await self.session.scalar(
            select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update(),
        )
        if not row:
            raise fail("ALREADY_HANDLED")
        if row.pay_batch_id is not None:
            raise fail("SESSION_LOCKED_PAID")
        if row.status == SessionStatus.open:
            raise fail("SESSION_OPEN")
        if len(reason.strip()) < 5 or len(reason) > 200:
            raise fail("REASON_REQUIRED", 422)
        if new_check_out_vn <= new_check_in_vn or new_check_in_vn.date() != new_check_out_vn.date():
            raise fail("INVALID_CHECKOUT_TIME", 422)
        if new_check_in_vn.date() != row.work_date:
            raise fail("INVALID_CHECKOUT_TIME", 422)

        other_rows = (await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == row.employee_id,
            WorkSessionOrm.work_date == row.work_date,
            WorkSessionOrm.id != row.id,
            WorkSessionOrm.status != SessionStatus.open,
        ))).all()
        for other in other_rows:
            other_in = _vn(other.check_in_at)
            other_out = _vn(other.check_out_at) if other.check_out_at else None
            if other_out and new_check_in_vn < other_out and new_check_out_vn > other_in:
                raise fail("SESSION_OVERLAP")

        old_value = {
            "check_in_at": row.check_in_at.isoformat(),
            "check_out_at": row.check_out_at.isoformat() if row.check_out_at else None,
            "minutes": row.minutes,
            "amount_raw": str(row.amount_raw) if row.amount_raw is not None else None,
        }
        row.check_in_at = new_check_in_vn
        row.check_out_at = new_check_out_vn
        row.work_date = new_check_in_vn.date()
        _recalculate_session(row)
        new_value = {
            "check_in_at": row.check_in_at.isoformat(),
            "check_out_at": row.check_out_at.isoformat() if row.check_out_at else None,
            "minutes": row.minutes,
            "amount_raw": str(row.amount_raw) if row.amount_raw is not None else None,
        }
        self.session.add(AuditLogOrm(
            actor_id=actor.id,
            action="session_edit",
            entity_type="work_session",
            entity_id=row.id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        ))
        self.session.add(_event("session_updated", {
            "session_id": row.id,
            "employee_id": row.employee_id,
            "old": old_value,
            "new": new_value,
            "reason": reason,
        }))
        await self.session.flush()
        return row

    async def escalate(self, day: date | None = None) -> list[WorkSessionOrm]:
        day = day or _vn(self.clock.now()).date()
        rows = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.status == SessionStatus.open, WorkSessionOrm.work_date == day).with_for_update())).all())
        for row in rows:
            row.status, row.review_reason = SessionStatus.needs_review, "forgot_checkout"
        return rows

    async def sweep_stale(self) -> list[WorkSessionOrm]:
        today = _vn(self.clock.now()).date()
        rows = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.status == SessionStatus.open, WorkSessionOrm.work_date < today).with_for_update())).all())
        for row in rows:
            row.status, row.review_reason = SessionStatus.needs_review, "forgot_checkout"
        return rows


class PayrollService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def eligible_sessions(self, employee_id: int, day: date, lock: bool = False) -> list[WorkSessionOrm]:
        query = select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee_id,
            WorkSessionOrm.work_date == day,
            WorkSessionOrm.status == SessionStatus.closed,
            WorkSessionOrm.pay_batch_id.is_(None),
        )
        if lock:
            query = query.with_for_update()
        rows = list((await self.session.scalars(query)).all())
        return [row for row in rows if not _has_unreviewed_flags(row)]

    async def _paid_amount(self, employee_id: int, day: date) -> int:
        paid = await self.session.scalar(select(func.coalesce(func.sum(PayBatchOrm.amount), 0)).where(
            PayBatchOrm.employee_id == employee_id, PayBatchOrm.work_date == day))
        return int(paid or 0)

    async def _paid_sessions_raw(self, employee_id: int, day: date) -> Decimal:
        paid_sessions_raw = await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(
            WorkSessionOrm.employee_id == employee_id, WorkSessionOrm.work_date == day,
            WorkSessionOrm.pay_batch_id.is_not(None)))
        return Decimal(paid_sessions_raw or 0)

    async def _payroll_summary(self, employee: EmployeeOrm, day: date) -> dict:
        eligible = await self.eligible_sessions(employee.id, day)
        all_sessions = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee.id, WorkSessionOrm.work_date == day))).all())
        paid = await self._paid_amount(employee.id, day)
        raw = await self._paid_sessions_raw(employee.id, day)
        raw += sum((row.amount_raw or Decimal(0) for row in eligible), Decimal(0))
        rounded = ceil_money(raw) if raw else 0
        pending_amount = max(0, rounded - paid)
        unreviewed = [row.id for row in all_sessions if _has_unreviewed_flags(row)]
        needs_review = [row.id for row in all_sessions if row.status == SessionStatus.needs_review]
        has_open = any(row.status == SessionStatus.open for row in all_sessions)
        pending_reason = None
        if has_open:
            pending_reason = "open_session"
        elif unreviewed:
            pending_reason = "unreviewed_gps"
        elif needs_review:
            pending_reason = "forgot_checkout"
        return {
            "employee_id": employee.id,
            "code": employee.code,
            "full_name": employee.full_name,
            "work_date": str(day),
            "hourly_rate": await current_hourly_rate(self.session, employee.id, day),
            "closed_minutes": sum((row.minutes or 0) for row in all_sessions if row.status == SessionStatus.closed),
            "eligible_minutes": sum((row.minutes or 0) for row in eligible),
            "eligible_session_ids": [row.id for row in eligible],
            "paid_amount": paid,
            "day_total_rounded": rounded,
            "pending_amount": pending_amount,
            "can_approve": bool(eligible),
            "unreviewed_flag_session_ids": unreviewed,
            "has_open_session": has_open,
            "needs_review_session_ids": needs_review,
            "pending_reason": pending_reason,
        }

    async def list_payroll(self, day: date) -> list[dict]:
        employees = list((await self.session.scalars(select(EmployeeOrm).where(
            EmployeeOrm.role == EmployeeRole.employee,
            EmployeeOrm.is_active.is_(True),
        ).order_by(EmployeeOrm.code))).all())
        return [await self._payroll_summary(employee, day) for employee in employees]

    async def get_employee_payroll_detail(self, employee_id: int, day: date) -> dict:
        employee = await self.session.get(EmployeeOrm, employee_id)
        if not employee:
            raise fail("NOT_REGISTERED", 404)
        summary = await self._payroll_summary(employee, day)
        sessions = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee_id,
            WorkSessionOrm.work_date == day,
        ).order_by(WorkSessionOrm.check_in_at))).all())
        batches = list((await self.session.scalars(select(PayBatchOrm).where(
            PayBatchOrm.employee_id == employee_id,
            PayBatchOrm.work_date == day,
        ).order_by(PayBatchOrm.batch_no))).all())
        summary.update({
            "sessions": [session_dict(row) | {
                "pay_batch_id": row.pay_batch_id,
                "is_locked": row.pay_batch_id is not None,
            } for row in sessions],
            "batches": [{
                "id": batch.id,
                "batch_no": batch.batch_no,
                "amount": batch.amount,
                "approved_by": batch.approved_by,
                "approved_at": iso_vn(batch.approved_at),
            } for batch in batches],
        })
        return summary

    async def approve_one(self, actor: EmployeeOrm, employee_id: int, day: date) -> PayBatchOrm:
        eligible = await self.eligible_sessions(employee_id, day, lock=True)
        if not eligible:
            raise fail("NO_ELIGIBLE_SESSIONS")
        raw = await self._paid_sessions_raw(employee_id, day)
        raw += sum((x.amount_raw or Decimal(0) for x in eligible), Decimal(0))
        rounded = ceil_money(raw)
        paid = await self._paid_amount(employee_id, day)
        amount = max(0, rounded - paid)
        batch_no = int(await self.session.scalar(select(func.coalesce(func.max(PayBatchOrm.batch_no), 0)).where(
            PayBatchOrm.employee_id == employee_id, PayBatchOrm.work_date == day)) or 0) + 1
        batch = PayBatchOrm(employee_id=employee_id, work_date=day, batch_no=batch_no,
                            amount=amount, day_total_rounded_at_approval=rounded,
                            approved_by=actor.id, approved_at=_vn(self.clock.now()))
        self.session.add(batch)
        await self.session.flush()
        for row in eligible:
            row.pay_batch_id = batch.id
        self.session.add(AuditLogOrm(actor_id=actor.id, action="batch_approved", entity_type="pay_batch", entity_id=batch.id))
        self.session.add(_event("batch_paid", {"batch_id": batch.id, "employee_id": employee_id,
                                               "amount": amount, "session_ids": [x.id for x in eligible]}))
        employee = await self.session.get(EmployeeOrm, employee_id)
        notice = _notice(f"batch-paid:{batch.id}", employee.telegram_id if employee else None,
                         "batch_paid", {"batch_no": batch_no, "date": fmt_date_vn(day), "amount": amount,
                                        "paid_total": paid + amount, "button": _tab_button("Mở ứng dụng", "history")})
        if notice:
            self.session.add(notice)
        return batch

    async def approve(self, actor: EmployeeOrm, employee_ids: list[int], day: date) -> list[PayBatchOrm]:
        batches = []
        for employee_id in employee_ids:
            try:
                batch = await self.approve_one(actor, employee_id, day)
            except Exception as exc:
                if getattr(exc, "code", None) == "NO_ELIGIBLE_SESSIONS":
                    continue
                raise
            batches.append(batch)
        if not batches:
            raise fail("NO_ELIGIBLE_SESSIONS")
        await self.session.flush()
        return batches


class HistoryService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    def _pending_reason(self, row: WorkSessionOrm) -> str | None:
        if row.pay_batch_id:
            return None
        if row.status == SessionStatus.open:
            return "dang_mo"
        if row.status == SessionStatus.needs_review:
            return "cho_xu_ly"
        if _has_unreviewed_flags(row):
            return "co_co_gps"
        return "cho_duyet"

    async def _output_items(self, session_id: int) -> list[dict]:
        rows = (await self.session.execute(select(
            ProductOrm.code, ProductOrm.name,
            func.coalesce(OutputItemOrm.bags, 0), func.coalesce(OutputItemOrm.kg, 0),
        ).join(OutputItemOrm, OutputItemOrm.product_id == ProductOrm.id)
         .join(OutputLogOrm, OutputLogOrm.id == OutputItemOrm.output_log_id)
         .where(OutputLogOrm.work_session_id == session_id)
         .order_by(ProductOrm.sort_order))).all()
        return [{"code": x[0], "name": x[1], "bags": int(x[2]), "kg": float(x[3])} for x in rows]

    async def history(self, employee: EmployeeOrm, start: date | None, end: date | None) -> dict:
        today = _vn(self.clock.now()).date()
        end = end or today
        start = start or (end - timedelta(days=29))
        sessions = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee.id,
            WorkSessionOrm.work_date.between(start, end),
        ).order_by(WorkSessionOrm.work_date.desc(), WorkSessionOrm.check_in_at))).all())
        batches = list((await self.session.scalars(select(PayBatchOrm).where(
            PayBatchOrm.employee_id == employee.id,
            PayBatchOrm.work_date.between(start, end),
        ).order_by(PayBatchOrm.work_date.desc(), PayBatchOrm.batch_no))).all())
        by_batch = {batch.id: [] for batch in batches}
        unpaid_by_day: dict[date, list[dict]] = {}
        for row in sessions:
            data = session_dict(row) | {
                "pay_batch_id": row.pay_batch_id,
                "pending_reason": self._pending_reason(row),
                "output": await self._output_items(row.id),
            }
            if row.pay_batch_id in by_batch:
                by_batch[row.pay_batch_id].append(data)
            elif row.pay_batch_id is None:
                unpaid_by_day.setdefault(row.work_date, []).append(data)
        days = []
        all_days = sorted({*(row.work_date for row in sessions), *(b.work_date for b in batches)}, reverse=True)
        for day in all_days:
            day_batches = []
            for batch in [b for b in batches if b.work_date == day]:
                day_batches.append({
                    "id": batch.id,
                    "batch_no": batch.batch_no,
                    "amount": batch.amount,
                    "approved_at": iso_vn(batch.approved_at),
                    "sessions": by_batch.get(batch.id, []),
                })
            paid = sum(b["amount"] for b in day_batches)
            eligible_raw = sum((row.amount_raw or Decimal(0) for row in sessions
                                if row.work_date == day and row.pay_batch_id is None
                                and row.status == SessionStatus.closed and not _has_unreviewed_flags(row)), Decimal(0))
            pending = 0
            if eligible_raw:
                paid_raw = await PayrollService(self.session)._paid_sessions_raw(employee.id, day)
                pending = max(0, ceil_money(paid_raw + eligible_raw) - paid)
            days.append({
                "date": day,
                "total_amount": paid + pending,
                "batches": day_batches,
                "unpaid_sessions": unpaid_by_day.get(day, []),
            })
        return {"from": start, "to": end, "days": days}


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def bounds(period: str, day: date) -> tuple[date, date]:
        if period == "day":
            return day, day
        if period == "week":
            start = day - timedelta(days=day.weekday())
            return start, start + timedelta(days=6)
        start = day.replace(day=1)
        following = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, following - timedelta(days=1)

    async def _salary_for_days(self, start: date, end: date, employee_id: int | None = None) -> dict[date, dict[str, int]]:
        employees = [employee_id] if employee_id else list((await self.session.scalars(
            select(EmployeeOrm.id).where(EmployeeOrm.role == EmployeeRole.employee)
        )).all())
        result: dict[date, dict[str, int]] = {}
        current = start
        while current <= end:
            result[current] = {"paid": 0, "pending": 0, "total": 0}
            for emp_id in employees:
                paid = int(await self.session.scalar(select(func.coalesce(func.sum(PayBatchOrm.amount), 0)).where(
                    PayBatchOrm.employee_id == emp_id, PayBatchOrm.work_date == current)) or 0)
                raw = Decimal(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(
                    WorkSessionOrm.employee_id == emp_id,
                    WorkSessionOrm.work_date == current,
                    WorkSessionOrm.status == SessionStatus.closed,
                )) or 0)
                pending = max(0, ceil_money(raw) - paid) if raw else 0
                result[current]["paid"] += paid
                result[current]["pending"] += pending
            result[current]["total"] = result[current]["paid"] + result[current]["pending"]
            current += timedelta(days=1)
        return result

    async def summary(self, period: str, day: date, employee_id: int | None = None) -> dict:
        start, end = self.bounds(period, day)
        filters = [WorkSessionOrm.work_date.between(start, end), WorkSessionOrm.status == SessionStatus.closed]
        if employee_id:
            filters.append(WorkSessionOrm.employee_id == employee_id)
        minutes = int(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.minutes), 0)).where(*filters)) or 0)
        production = (await self.session.execute(select(func.coalesce(func.sum(OutputItemOrm.bags), 0),
            func.coalesce(func.sum(OutputItemOrm.kg), 0)).select_from(OutputItemOrm)
            .join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
        salary_days = await self._salary_for_days(start, end, employee_id)
        paid = sum(x["paid"] for x in salary_days.values())
        pending = sum(x["pending"] for x in salary_days.values())
        return {"from": start, "to": end, "minutes": minutes,
                "salary": {"paid": paid, "pending": pending, "total": paid + pending},
                "paid": paid, "pending": pending, "total": paid + pending,
                "bags": int(production[0]), "kg": float(production[1])}

    async def products(self, period: str, day: date, employee_id: int | None = None) -> list[dict]:
        start, end = self.bounds(period, day)
        products = list((await self.session.scalars(select(ProductOrm).order_by(ProductOrm.sort_order))).all())
        result = []
        for product in products:
            filters = [WorkSessionOrm.work_date.between(start, end), OutputItemOrm.product_id == product.id]
            if employee_id:
                filters.append(WorkSessionOrm.employee_id == employee_id)
            bags, kg = (await self.session.execute(select(
                func.coalesce(func.sum(OutputItemOrm.bags), 0),
                func.coalesce(func.sum(OutputItemOrm.kg), 0),
            ).select_from(OutputItemOrm).join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
            result.append({"code": product.code, "name": product.name, "bags": int(bags), "kg": float(kg)})
        return result

    async def timeseries(self, period: str, day: date, employee_id: int | None = None) -> list[dict]:
        start, end = self.bounds(period, day)
        salary_days = await self._salary_for_days(start, end, employee_id)
        rows = []
        current = start
        while current <= end:
            filters = [WorkSessionOrm.work_date == current, WorkSessionOrm.status == SessionStatus.closed]
            if employee_id:
                filters.append(WorkSessionOrm.employee_id == employee_id)
            minutes = int(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.minutes), 0)).where(*filters)) or 0)
            bags, kg = (await self.session.execute(select(func.coalesce(func.sum(OutputItemOrm.bags), 0),
                func.coalesce(func.sum(OutputItemOrm.kg), 0)).select_from(OutputItemOrm)
                .join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
            salary = salary_days[current]
            rows.append({"date": current, "minutes": minutes, "salary": salary["total"],
                         "paid": salary["paid"], "pending": salary["pending"],
                         "bags": int(bags), "kg": float(kg)})
            current += timedelta(days=1)
        return rows


class EmployeeService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def list(self, q: str | None = None, active: bool | None = None) -> list[dict]:
        query = select(EmployeeOrm).where(EmployeeOrm.role == EmployeeRole.employee)
        if active is not None:
            query = query.where(EmployeeOrm.is_active.is_(active))
        if q:
            like = f"%{q.strip()}%"
            query = query.where(or_(EmployeeOrm.code.ilike(like), EmployeeOrm.full_name.ilike(like)))
        rows = (await self.session.scalars(query.order_by(EmployeeOrm.code))).all()
        return [await employee_admin_dict(self.session, row, _vn(self.clock.now()).date()) for row in rows]

    async def create(self, actor: EmployeeOrm, code: str, name: str, hourly_rate: int, effective_from: date) -> dict:
        employee, invite = await create_employee(self.session, actor, code, name, hourly_rate, effective_from, self.clock)
        data = await employee_admin_dict(self.session, employee, effective_from)
        return data | {"invite_url": invite}

    async def lock(self, actor: EmployeeOrm, employee_id: int) -> dict:
        row = await self.session.get(EmployeeOrm, employee_id)
        if not row:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        if row.id == actor.id:
            raise fail("FORBIDDEN", 403)
        if await has_open_session(self.session, employee_id):
            raise fail("EMPLOYEE_HAS_OPEN_SESSION")
        row.is_active = False
        self.session.add(AuditLogOrm(actor_id=actor.id, action="employee_locked", entity_type="employee", entity_id=row.id))
        return await employee_admin_dict(self.session, row, _vn(self.clock.now()).date())

    async def unlock(self, actor: EmployeeOrm, employee_id: int) -> dict:
        row = await self.session.get(EmployeeOrm, employee_id)
        if not row:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        row.is_active = True
        self.session.add(AuditLogOrm(actor_id=actor.id, action="employee_unlocked", entity_type="employee", entity_id=row.id))
        return await employee_admin_dict(self.session, row, _vn(self.clock.now()).date())

    async def regenerate_invite(self, actor: EmployeeOrm, employee_id: int) -> dict:
        row = await self.session.get(EmployeeOrm, employee_id)
        if not row:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        if row.telegram_id:
            data = await employee_admin_dict(self.session, row, _vn(self.clock.now()).date())
            return data | {"invite_url": None}
        invite = await create_invite(self.session, row, actor.id, self.clock.now())
        self.session.add(AuditLogOrm(actor_id=actor.id, action="invite_regenerated", entity_type="employee", entity_id=row.id))
        data = await employee_admin_dict(self.session, row, _vn(self.clock.now()).date())
        return data | {"invite_url": invite}

    async def rates(self, employee_id: int) -> list[dict]:
        employee = await self.session.get(EmployeeOrm, employee_id)
        if not employee:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        rows = (await self.session.scalars(select(RateHistoryOrm).where(
            RateHistoryOrm.employee_id == employee_id,
        ).order_by(RateHistoryOrm.effective_from.desc()))).all()
        return [{"id": x.id, "hourly_rate": x.hourly_rate, "effective_from": x.effective_from} for x in rows]

    async def add_rate(self, actor: EmployeeOrm, employee_id: int, hourly_rate: int, effective_from: date) -> dict:
        employee = await self.session.get(EmployeeOrm, employee_id)
        if not employee:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        today = _vn(self.clock.now()).date()
        if effective_from < today:
            raise fail("RATE_DATE_IN_PAST", 422)
        exists = await self.session.scalar(select(RateHistoryOrm.id).where(
            RateHistoryOrm.employee_id == employee_id,
            RateHistoryOrm.effective_from == effective_from,
        ))
        if exists:
            raise fail("RATE_DATE_EXISTS", 409)
        row = RateHistoryOrm(employee_id=employee_id, hourly_rate=hourly_rate,
                             effective_from=effective_from, created_by=actor.id)
        self.session.add(row)
        self.session.add(AuditLogOrm(actor_id=actor.id, action="rate_added",
                                     entity_type="employee", entity_id=employee_id,
                                     new_value={"hourly_rate": hourly_rate, "effective_from": str(effective_from)}))
        await self.session.flush()
        return {"id": row.id, "hourly_rate": row.hourly_rate, "effective_from": row.effective_from}


async def create_employee(session: AsyncSession, actor: EmployeeOrm, code: str, name: str,
                          hourly_rate: int, effective_from: date,
                          clock: Clock | None = None) -> tuple[EmployeeOrm, str]:
    clock = clock or Clock()
    today = _vn(clock.now()).date()
    if effective_from < today or hourly_rate <= 0:
        raise fail("INVALID_EMPLOYEE_DATA", 422)
    employee = EmployeeOrm(code=code, full_name=name, role=EmployeeRole.employee)
    session.add(employee)
    await session.flush()
    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=hourly_rate,
                               effective_from=effective_from, created_by=actor.id))
    invite = await create_invite(session, employee, actor.id, clock.now())
    session.add(AuditLogOrm(actor_id=actor.id, action="employee_created", entity_type="employee", entity_id=employee.id))
    return employee, invite


def session_dict(row: WorkSessionOrm | None) -> dict | None:
    if not row:
        return None
    return {"id": row.id, "employee_id": row.employee_id, "work_date": str(row.work_date),
            "check_in_at": iso_vn(row.check_in_at), "check_out_at": iso_vn(row.check_out_at),
            "minutes": row.minutes, "rate_snapshot": row.rate_snapshot,
            "amount_raw": float(row.amount_raw) if row.amount_raw is not None else None,
            "status": row.status.value, "review_reason": row.review_reason, "flags": row.flags or [],
            "check_in_accuracy_m": float(row.check_in_accuracy_m) if row.check_in_accuracy_m is not None else None,
            "check_in_distance_m": float(row.check_in_distance_m),
            "check_out_accuracy_m": float(row.check_out_accuracy_m) if row.check_out_accuracy_m is not None else None,
            "check_out_distance_m": float(row.check_out_distance_m) if row.check_out_distance_m is not None else None}
