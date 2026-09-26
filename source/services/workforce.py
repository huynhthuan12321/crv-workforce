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


def _has_unreviewed_flags(row: WorkSessionOrm) -> bool:
    return bool(row.flags) and row.flags_reviewed_at is None


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
        return {"session_id": session_id, "total_kg": float(total), "locked_at": output.locked_at}


class ReviewService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def pending(self) -> list[dict]:
        rows = (await self.session.scalars(select(WorkSessionOrm).where(or_(
            WorkSessionOrm.status == SessionStatus.needs_review,
            WorkSessionOrm.status == SessionStatus.closed,
        )).order_by(WorkSessionOrm.check_in_at))).all()
        return [session_dict(x) for x in rows
                if x.status == SessionStatus.needs_review or _has_unreviewed_flags(x)]

    async def mark_flags(self, actor: EmployeeOrm, session_id: int) -> WorkSessionOrm:
        row = await self.session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update())
        if not row or row.flags_reviewed_at:
            raise fail("ALREADY_HANDLED")
        row.flags_reviewed_by, row.flags_reviewed_at = actor.id, _vn(self.clock.now())
        self.session.add(AuditLogOrm(actor_id=actor.id, action="flags_reviewed", entity_type="work_session", entity_id=row.id))
        return row

    async def list_resolved(self) -> list[dict]:
        rows = (await self.session.scalars(select(WorkSessionOrm).where(or_(
            WorkSessionOrm.flags_reviewed_at.is_not(None),
            WorkSessionOrm.closed_by.is_not(None),
        )).order_by(WorkSessionOrm.updated_at.desc()))).all()
        resolved = []
        for row in rows:
            resolved_by = row.flags_reviewed_by or row.closed_by
            actor = await self.session.get(EmployeeOrm, resolved_by) if resolved_by else None
            data = session_dict(row)
            data.update({
                "resolved_by": resolved_by,
                "resolved_by_name": actor.full_name if actor else None,
                "resolved_at": row.flags_reviewed_at or row.updated_at,
                "resolved_action": "flags_reviewed" if row.flags_reviewed_at else "session_closed",
            })
            resolved.append(data)
        return resolved

    async def close_forgotten(self, actor: EmployeeOrm, session_id: int, check_out: datetime, reason: str) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        check_out_vn = to_vn(check_out)
        row = await self.session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update())
        if not row or row.status != SessionStatus.needs_review:
            raise fail("ALREADY_HANDLED")
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
                         "forgot_session_closed", {"session_id": row.id, "work_date": str(row.work_date)})
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
        return {
            "employee_id": employee.id,
            "code": employee.code,
            "full_name": employee.full_name,
            "work_date": str(day),
            "closed_minutes": sum((row.minutes or 0) for row in all_sessions if row.status == SessionStatus.closed),
            "eligible_minutes": sum((row.minutes or 0) for row in eligible),
            "eligible_session_ids": [row.id for row in eligible],
            "paid_amount": paid,
            "day_total_rounded": rounded,
            "pending_amount": pending_amount,
            "can_approve": bool(eligible),
            "unreviewed_flag_session_ids": unreviewed,
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
            "sessions": [session_dict(row) | {"pay_batch_id": row.pay_batch_id} for row in sessions],
            "batches": [{
                "id": batch.id,
                "batch_no": batch.batch_no,
                "amount": batch.amount,
                "approved_by": batch.approved_by,
                "approved_at": batch.approved_at,
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
                         "batch_paid", {"batch_no": batch_no, "date": str(day), "amount": amount, "paid_total": paid + amount})
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


async def create_employee(session: AsyncSession, actor: EmployeeOrm, code: str, name: str,
                          hourly_rate: int, effective_from: date) -> tuple[EmployeeOrm, str]:
    today = _vn(Clock().now()).date()
    if effective_from < today or hourly_rate <= 0:
        raise fail("INVALID_EMPLOYEE_DATA", 422)
    employee = EmployeeOrm(code=code, full_name=name, role=EmployeeRole.employee)
    session.add(employee)
    await session.flush()
    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=hourly_rate,
                               effective_from=effective_from, created_by=actor.id))
    code_value = secrets.token_urlsafe(32)
    session.add(InviteCodeOrm(employee_id=employee.id, code=code_value, created_by=actor.id,
                              expires_at=Clock().now() + timedelta(days=settings.rules.invite_expire_days)))
    session.add(AuditLogOrm(actor_id=actor.id, action="employee_created", entity_type="employee", entity_id=employee.id))
    return employee, f"https://t.me/{settings.tg.bot_username}/{settings.tg.miniapp_short_name}?startapp={code_value}"


def session_dict(row: WorkSessionOrm | None) -> dict | None:
    if not row:
        return None
    return {"id": row.id, "employee_id": row.employee_id, "work_date": str(row.work_date),
            "check_in_at": row.check_in_at, "check_out_at": row.check_out_at,
            "minutes": row.minutes, "rate_snapshot": row.rate_snapshot,
            "amount_raw": float(row.amount_raw) if row.amount_raw is not None else None,
            "status": row.status.value, "flags": row.flags or [],
            "check_in_distance_m": float(row.check_in_distance_m),
            "check_out_distance_m": float(row.check_out_distance_m) if row.check_out_distance_m is not None else None}
