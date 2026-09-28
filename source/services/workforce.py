import math
import secrets
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from source.config import settings
from source.database.models import (
    EmployeeLocationAssignmentOrm,
    AuditLogOrm, ConsentTextOrm, EmployeeOrm, InviteCodeOrm,
    LocationConsentOrm, NotificationOutboxOrm, OutputItemOrm, OutputLogOrm,
    PayBatchOrm, ProductOrm, RateHistoryOrm, SyncOutboxOrm, WorkLocationOrm, WorkSessionOrm,
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


def _flags(distance: float, accuracy: float, radius_m: int | Decimal | None) -> list[str]:
    result = []
    radius = Decimal(str(radius_m or 0))
    if Decimal(str(distance)) > radius:
        result.append("gps_out_of_range")
    if accuracy > settings.rules.gps_max_accuracy_m:
        result.append("gps_low_accuracy")
    return result


def _event(event_type: str, payload: dict) -> SyncOutboxOrm:
    return SyncOutboxOrm(event_type=event_type, payload={
        "schema_version": 2,
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": iso_vn(Clock().now()),
        **payload,
    })


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


def _flag_source(row: WorkSessionOrm) -> str | None:
    if row.flag_source:
        return row.flag_source
    if not row.flags:
        return None
    radius = Decimal(str(row.location_radius_m_snapshot or 100))
    in_flagged = False
    out_flagged = False
    if "gps_out_of_range" in (row.flags or []):
        in_flagged = in_flagged or (
            row.check_in_distance_m is not None
            and Decimal(row.check_in_distance_m) > radius
        )
        out_flagged = out_flagged or (
            row.check_out_distance_m is not None
            and Decimal(row.check_out_distance_m) > radius
        )
    if "gps_low_accuracy" in (row.flags or []):
        in_flagged = in_flagged or (
            row.check_in_accuracy_m is not None
            and Decimal(row.check_in_accuracy_m) > Decimal(str(settings.rules.gps_max_accuracy_m))
        )
        out_flagged = out_flagged or (
            row.check_out_accuracy_m is not None
            and Decimal(row.check_out_accuracy_m) > Decimal(str(settings.rules.gps_max_accuracy_m))
        )
    if in_flagged and out_flagged:
        return "both"
    if out_flagged:
        return "check_out"
    if in_flagged:
        return "check_in"
    return "check_in"


def _review_type(row: WorkSessionOrm) -> str | None:
    if row.status == SessionStatus.needs_review:
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


async def current_location_assignment(session: AsyncSession, employee_id: int, lock: bool = False) -> EmployeeLocationAssignmentOrm | None:
    query = select(EmployeeLocationAssignmentOrm).where(
        EmployeeLocationAssignmentOrm.employee_id == employee_id,
        EmployeeLocationAssignmentOrm.effective_to.is_(None),
    )
    if lock:
        query = query.with_for_update()
    return await session.scalar(query)


async def current_work_location(session: AsyncSession, employee_id: int) -> WorkLocationOrm | None:
    assignment = await current_location_assignment(session, employee_id)
    if not assignment:
        return None
    return await session.get(WorkLocationOrm, assignment.location_id)


async def employee_admin_dict(session: AsyncSession, row: EmployeeOrm, day: date | None = None) -> dict:
    location = await current_work_location(session, row.id) if row.role == EmployeeRole.employee else None
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
        "work_location": location_dict(location) if location else None,
    }


async def employee_ref(session: AsyncSession, employee_id: int) -> dict:
    employee = await session.get(EmployeeOrm, employee_id)
    return {"id": employee_id, "code": employee.code if employee else "", "name": employee.full_name if employee else ""}


def session_location_ref(row: WorkSessionOrm) -> dict:
    return {"id": row.work_location_id, "code": row.location_code_snapshot, "name": row.location_name_snapshot}


def session_event_ref(row: WorkSessionOrm) -> dict:
    return {
        "id": row.id,
        "work_date": str(row.work_date),
        "check_in_at": iso_vn(row.check_in_at),
        "check_out_at": iso_vn(row.check_out_at),
        "minutes": row.minutes,
        "rate_snapshot": row.rate_snapshot,
        "amount_raw": str(row.amount_raw) if row.amount_raw is not None else None,
        "flags": row.flags or [],
        "flag_source": _flag_source(row),
        "location_id": row.work_location_id,
        "location": session_location_ref(row),
    }


def location_dict(row: WorkLocationOrm | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "location_type": row.location_type,
        "address": row.address,
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "radius_m": row.radius_m,
        "coordinate_source": row.coordinate_source,
        "location_accuracy_m": float(row.location_accuracy_m) if row.location_accuracy_m is not None else None,
        "is_active": row.is_active,
        "created_at": iso_vn(row.created_at),
        "updated_at": iso_vn(row.updated_at),
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

    async def _nearby_location(self, assigned_id: int, lat: float, lng: float) -> tuple[int | None, Decimal | None]:
        rows = (await self.session.scalars(select(WorkLocationOrm).where(
            WorkLocationOrm.is_active.is_(True),
            WorkLocationOrm.id != assigned_id,
        ))).all()
        best_id: int | None = None
        best_distance: float | None = None
        for location in rows:
            distance = haversine_m(lat, lng, float(location.latitude), float(location.longitude))
            if distance <= location.radius_m and (best_distance is None or distance < best_distance):
                best_id = location.id
                best_distance = distance
        return best_id, Decimal(str(best_distance)) if best_distance is not None else None

    async def _assigned_location_for_check_in(self, employee_id: int) -> WorkLocationOrm:
        await self.session.scalar(select(EmployeeOrm).where(EmployeeOrm.id == employee_id).with_for_update())
        assignment = await current_location_assignment(self.session, employee_id, lock=True)
        if not assignment:
            raise fail("LOCATION_REQUIRED", 409)
        location = await self.session.scalar(select(WorkLocationOrm).where(
            WorkLocationOrm.id == assignment.location_id,
        ).with_for_update(read=True))
        if not location or not location.is_active:
            raise fail("LOCATION_INACTIVE")
        return location

    async def check_in(self, employee: EmployeeOrm, lat: float, lng: float, accuracy_m: float) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        _, consented = await current_consent(self.session, employee.id, now)
        if not consented:
            raise fail("LOCATION_CONSENT_REQUIRED")
        if now.time() >= settings.rules.checkin_cutoff:
            raise fail("CHECKIN_AFTER_CUTOFF")
        location = await self._assigned_location_for_check_in(employee.id)
        opened = await self.session.scalar(select(WorkSessionOrm.id).where(
            WorkSessionOrm.employee_id == employee.id, WorkSessionOrm.status == SessionStatus.open))
        if opened:
            raise fail("SESSION_ALREADY_OPEN")
        distance = haversine_m(lat, lng, float(location.latitude), float(location.longitude))
        nearby_id, nearby_distance = await self._nearby_location(location.id, lat, lng)
        row = WorkSessionOrm(
            employee_id=employee.id, work_date=now.date(), check_in_at=now,
            check_in_lat=Decimal(str(lat)), check_in_lng=Decimal(str(lng)),
            check_in_accuracy_m=Decimal(str(accuracy_m)), check_in_distance_m=Decimal(str(distance)),
            work_location_id=location.id,
            location_code_snapshot=location.code,
            location_name_snapshot=location.name,
            location_lat_snapshot=location.latitude,
            location_lng_snapshot=location.longitude,
            location_radius_m_snapshot=location.radius_m,
            nearby_location_id=nearby_id,
            nearby_location_distance_m=nearby_distance,
            rate_snapshot=await self._rate(employee.id, now.date()),
            status=SessionStatus.open, flags=_flags(distance, accuracy_m, location.radius_m),
        )
        row.flag_source = _flag_source(row)
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
        distance = haversine_m(lat, lng, float(row.location_lat_snapshot), float(row.location_lng_snapshot))
        row.check_out_at = now
        row.check_out_lat, row.check_out_lng = Decimal(str(lat)), Decimal(str(lng))
        row.check_out_accuracy_m, row.check_out_distance_m = Decimal(str(accuracy_m)), Decimal(str(distance))
        row.flags = list(dict.fromkeys([*(row.flags or []), *_flags(distance, accuracy_m, row.location_radius_m_snapshot)]))
        row.flag_source = _flag_source(row)
        row.minutes = max(0, int((now - _vn(row.check_in_at)).total_seconds() // 60))
        row.amount_raw = Decimal(row.minutes) * Decimal(row.rate_snapshot) / Decimal(60)
        row.status, row.closed_by = SessionStatus.closed, employee.id
        self.session.add(OutputLogOrm(work_session_id=row.id, locked_at=now + timedelta(minutes=settings.rules.output_edit_minutes)))
        self.session.add(_event("session_closed", {
            "employee": await employee_ref(self.session, employee.id),
            "location": session_location_ref(row),
            "session": session_event_ref(row),
        }))
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
        can_check_in = opened is None and now.time() < settings.rules.checkin_cutoff
        location = await current_work_location(self.session, employee.id)
        return {"open_session": session_dict(opened) if opened else None,
                "estimated_day_amount": ceil_money(raw), "paid_today": int(paid or 0),
                "server_now": iso_vn(now),
                "checkin_cutoff": settings.rules.checkin_cutoff.strftime("%H:%M"),
                "can_check_in": can_check_in,
                "work_location": location_dict(location) if location else None}


class WorkingService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def working_now(self, location_id: int | None = None) -> list[dict]:
        now = _vn(self.clock.now())
        filters = [
            WorkSessionOrm.status == SessionStatus.open,
            WorkSessionOrm.work_date == now.date(),
        ]
        if location_id:
            filters.append(WorkSessionOrm.work_location_id == location_id)
        rows = list((await self.session.scalars(select(WorkSessionOrm).where(*filters).order_by(WorkSessionOrm.check_in_at))).all())
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
                "server_now": iso_vn(now),
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
                "server_now": iso_vn(now),
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
        self.session.add(_event("output_submitted", {
            "employee": await employee_ref(self.session, work.employee_id),
            "location": session_location_ref(work),
            "session": {"id": session_id},
            "items": values,
        }))
        await self.session.flush()
        return {"session_id": session_id, "total_kg": float(total), "locked_at": iso_vn(output.locked_at)}


class ReviewService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def _review_item(self, row: WorkSessionOrm) -> dict:
        employee = await self.session.get(EmployeeOrm, row.employee_id)
        nearby = await self.session.get(WorkLocationOrm, row.nearby_location_id) if row.nearby_location_id else None
        return session_dict(row) | {
            "employee_code": employee.code if employee else "",
            "employee_name": employee.full_name if employee else "",
            "review_reason": row.review_reason,
            "nearby_location_name": nearby.name if nearby else None,
            "nearby_location_code": nearby.code if nearby else None,
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

    async def pending(self, type_: str | None = None, location_id: int | None = None) -> list[dict]:
        filters = [or_(
            WorkSessionOrm.status == SessionStatus.needs_review,
            WorkSessionOrm.status == SessionStatus.closed,
        )]
        if location_id:
            filters.append(WorkSessionOrm.work_location_id == location_id)
        rows = (await self.session.scalars(select(WorkSessionOrm).where(*filters).order_by(WorkSessionOrm.check_in_at))).all()
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

    async def list_resolved(self, type_: str | None = None, location_id: int | None = None) -> list[dict]:
        filters = [or_(
            WorkSessionOrm.flags_reviewed_at.is_not(None),
            WorkSessionOrm.closed_by.is_not(None),
        )]
        if location_id:
            filters.append(WorkSessionOrm.work_location_id == location_id)
        rows = (await self.session.scalars(select(WorkSessionOrm).where(*filters).order_by(WorkSessionOrm.updated_at.desc()))).all()
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

    def _checkout_details(self, min_check_out: datetime, max_check_out: datetime, overlap: WorkSessionOrm | None = None) -> dict:
        details = {"min_check_out": iso_vn(min_check_out), "max_check_out": iso_vn(max_check_out)}
        if overlap:
            details["overlap"] = {
                "id": overlap.id,
                "status": overlap.status.value,
                "check_in_at": iso_vn(overlap.check_in_at),
                "check_out_at": iso_vn(overlap.check_out_at) if overlap.check_out_at else None,
            }
        return details

    async def _checkout_context(self, row: WorkSessionOrm, check_in_vn: datetime) -> tuple[datetime, datetime, list[WorkSessionOrm]]:
        now = _vn(self.clock.now())
        min_check_out = check_in_vn + timedelta(minutes=1)
        others = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == row.employee_id,
            WorkSessionOrm.work_date == check_in_vn.date(),
            WorkSessionOrm.id != row.id,
        ).order_by(WorkSessionOrm.check_in_at))).all())
        next_starts = [_vn(other.check_in_at) for other in others if _vn(other.check_in_at) > check_in_vn]
        max_check_out = min([now, *next_starts])
        return min_check_out, max_check_out, others

    def _overlapping_session(self, check_in_vn: datetime, check_out_vn: datetime, others: list[WorkSessionOrm]) -> WorkSessionOrm | None:
        for other in others:
            other_in = _vn(other.check_in_at)
            other_out = _vn(other.check_out_at) if other.check_out_at else None
            if other_out:
                if check_in_vn < other_out and check_out_vn > other_in:
                    return other
            elif check_in_vn <= other_in < check_out_vn:
                return other
        return None

    async def _validate_checkout_interval(self, row: WorkSessionOrm, check_in_vn: datetime, check_out_vn: datetime) -> None:
        if check_out_vn <= check_in_vn or check_out_vn.date() != check_in_vn.date():
            raise fail("INVALID_CHECKOUT_TIME", 422)
        min_check_out, max_check_out, others = await self._checkout_context(row, check_in_vn)
        details = self._checkout_details(min_check_out, max_check_out)
        if check_out_vn > _vn(self.clock.now()):
            raise fail("CHECKOUT_IN_FUTURE", 422, details=details)
        overlap = self._overlapping_session(check_in_vn, check_out_vn, others)
        if overlap:
            raise fail("SESSION_OVERLAP", details=self._checkout_details(min_check_out, max_check_out, overlap))

    async def checkout_bounds(self, session_id: int) -> dict:
        row = await self.session.get(WorkSessionOrm, session_id)
        if not row:
            raise fail("ALREADY_HANDLED")
        check_in_vn = _vn(row.check_in_at)
        min_check_out, max_check_out, others = await self._checkout_context(row, check_in_vn)
        return {
            "session_id": row.id,
            "min_check_out": iso_vn(min_check_out),
            "max_check_out": iso_vn(max_check_out),
            "sessions": [session_dict(other) for other in others],
        }

    async def close_forgotten(self, actor: EmployeeOrm, session_id: int, check_out: datetime, reason: str) -> WorkSessionOrm:
        now = _vn(self.clock.now())
        check_out_vn = to_vn(check_out)
        row = await self.session.scalar(select(WorkSessionOrm).where(WorkSessionOrm.id == session_id).with_for_update())
        if not row or row.status != SessionStatus.needs_review:
            raise fail("ALREADY_HANDLED", details=await self._handled_details(row))
        if len(reason.strip()) < 5 or len(reason) > 200:
            raise fail("REASON_REQUIRED", 422)
        check_in_vn = _vn(row.check_in_at)
        if check_out_vn.date() != row.work_date:
            raise fail("INVALID_CHECKOUT_TIME", 422)
        await self._validate_checkout_interval(row, check_in_vn, check_out_vn)
        row.check_out_at = check_out_vn
        _recalculate_session(row)
        row.status, row.closed_by = SessionStatus.closed, actor.id
        self.session.add(OutputLogOrm(work_session_id=row.id, locked_at=now + timedelta(minutes=settings.rules.output_edit_minutes)))
        self.session.add(AuditLogOrm(actor_id=actor.id, action="session_close_by_manager", entity_type="work_session", entity_id=row.id, reason=reason))
        self.session.add(_event("session_closed", {
            "employee": await employee_ref(self.session, row.employee_id),
            "location": session_location_ref(row),
            "session": session_event_ref(row),
        }))
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
        await self._validate_checkout_interval(row, new_check_in_vn, new_check_out_vn)

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
            "employee": await employee_ref(self.session, row.employee_id),
            "location": session_location_ref(row),
            "session": {"id": row.id},
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

    async def _blocked_amount(self, employee_id: int, day: date, paid: int, pending_eligible: int) -> int:
        all_closed_raw = Decimal(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(
            WorkSessionOrm.employee_id == employee_id,
            WorkSessionOrm.work_date == day,
            WorkSessionOrm.status == SessionStatus.closed,
        )) or 0)
        all_closed_rounded = ceil_money(all_closed_raw) if all_closed_raw else 0
        return max(0, all_closed_rounded - paid - pending_eligible)

    async def _payroll_summary(self, employee: EmployeeOrm, day: date) -> dict:
        eligible = await self.eligible_sessions(employee.id, day)
        all_sessions = list((await self.session.scalars(select(WorkSessionOrm).where(
            WorkSessionOrm.employee_id == employee.id, WorkSessionOrm.work_date == day))).all())
        paid = await self._paid_amount(employee.id, day)
        raw = await self._paid_sessions_raw(employee.id, day)
        raw += sum((row.amount_raw or Decimal(0) for row in eligible), Decimal(0))
        rounded = ceil_money(raw) if raw else 0
        pending_amount = max(0, rounded - paid)
        unreviewed = [row.id for row in all_sessions if row.status == SessionStatus.closed and _has_unreviewed_flags(row)]
        needs_review = [row.id for row in all_sessions if row.status == SessionStatus.needs_review]
        has_open = any(row.status == SessionStatus.open for row in all_sessions)
        location_ids = sorted({row.work_location_id for row in all_sessions if row.work_location_id is not None})
        day_locations_map = {
            row.work_location_id: {
                "id": row.work_location_id,
                "code": row.location_code_snapshot,
                "name": row.location_name_snapshot,
            }
            for row in all_sessions
            if row.work_location_id is not None
        }
        day_locations = [day_locations_map[key] for key in sorted(day_locations_map)]
        location_names = [row["name"] for row in day_locations if row.get("name")]
        pending_reasons = []
        if unreviewed:
            pending_reasons.append("unreviewed_gps")
        if needs_review:
            pending_reasons.append("forgot_checkout")
        if has_open:
            pending_reasons.append("open_session")
        blocked_amount = await self._blocked_amount(employee.id, day, paid, pending_amount)
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
            "blocked_amount": blocked_amount,
            "can_approve": bool(eligible),
            "unreviewed_flag_session_ids": unreviewed,
            "has_open_session": has_open,
            "has_sessions": bool(all_sessions),
            "needs_review_session_ids": needs_review,
            "pending_reason": pending_reasons[0] if pending_reasons else None,
            "pending_reasons": pending_reasons,
            "work_location_ids": location_ids,
            "work_location_names": location_names,
            "day_locations": day_locations,
            "has_multiple_locations": len(location_ids) > 1,
        }

    async def list_payroll(self, day: date, location_id: int | None = None) -> list[dict]:
        query = select(EmployeeOrm).where(
            EmployeeOrm.role == EmployeeRole.employee,
            EmployeeOrm.is_active.is_(True),
        )
        if location_id:
            query = query.where(EmployeeOrm.id.in_(select(WorkSessionOrm.employee_id).where(
                WorkSessionOrm.work_date == day,
                WorkSessionOrm.work_location_id == location_id,
            )))
        employees = list((await self.session.scalars(query.order_by(EmployeeOrm.code))).all())
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
        employee = await self.session.get(EmployeeOrm, employee_id)
        location_map = {row.work_location_id: session_location_ref(row) for row in eligible if row.work_location_id is not None}
        self.session.add(_event("batch_paid", {
            "employee": await employee_ref(self.session, employee_id),
            "locations": list(location_map.values()),
            "batch": {"id": batch.id, "work_date": str(day), "batch_no": batch.batch_no,
                      "amount": amount, "approved_by": actor.id, "approved_at": iso_vn(batch.approved_at)},
            "sessions": [{"id": row.id, "location_id": row.work_location_id} for row in eligible],
        }))
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

    async def _output_state(self, session_id: int) -> dict:
        output = await self.session.scalar(select(OutputLogOrm).where(OutputLogOrm.work_session_id == session_id))
        if not output:
            return {"output_locked": True, "output_locked_at": None}
        locked_at = _vn(output.locked_at)
        return {"output_locked": _vn(self.clock.now()) >= locked_at, "output_locked_at": iso_vn(output.locked_at)}

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
            } | await self._output_state(row.id)
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
            blocked = 0
            if eligible_raw:
                paid_raw = await PayrollService(self.session)._paid_sessions_raw(employee.id, day)
                pending = max(0, ceil_money(paid_raw + eligible_raw) - paid)
            blocked = await PayrollService(self.session)._blocked_amount(employee.id, day, paid, pending)
            days.append({
                "date": day,
                "total_amount": paid + pending + blocked,
                "paid_amount": paid,
                "pending_amount": pending,
                "blocked_amount": blocked,
                "batches": day_batches,
                "unpaid_sessions": unpaid_by_day.get(day, []),
            })
        return {"from": start, "to": end, "days": days}


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def employees(self, q: str | None = None) -> list[dict]:
        query = select(EmployeeOrm).where(EmployeeOrm.role == EmployeeRole.employee)
        if q:
            like = f"%{q.strip()}%"
            query = query.where(or_(EmployeeOrm.code.ilike(like), EmployeeOrm.full_name.ilike(like)))
        rows = (await self.session.scalars(query.order_by(EmployeeOrm.code))).all()
        return [{"id": row.id, "code": row.code, "full_name": row.full_name, "is_active": row.is_active} for row in rows]

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
            result[current] = {
                "paid": 0,
                "pending": 0,
                "pending_eligible": 0,
                "pending_blocked": 0,
                "needs_review_count": 0,
                "total": 0,
            }
            payroll = PayrollService(self.session)
            for emp_id in employees:
                paid = int(await self.session.scalar(select(func.coalesce(func.sum(PayBatchOrm.amount), 0)).where(
                    PayBatchOrm.employee_id == emp_id, PayBatchOrm.work_date == current)) or 0)
                employee = await self.session.get(EmployeeOrm, emp_id)
                pending_eligible = 0
                if employee:
                    pending_eligible = int((await payroll._payroll_summary(employee, current))["pending_amount"])
                pending_blocked = await payroll._blocked_amount(emp_id, current, paid, pending_eligible)
                needs_review_count = int(await self.session.scalar(select(func.count()).select_from(WorkSessionOrm).where(
                    WorkSessionOrm.employee_id == emp_id,
                    WorkSessionOrm.work_date == current,
                    WorkSessionOrm.status == SessionStatus.needs_review,
                )) or 0)
                result[current]["paid"] += paid
                result[current]["pending_eligible"] += pending_eligible
                result[current]["pending_blocked"] += pending_blocked
                result[current]["needs_review_count"] += needs_review_count
                result[current]["pending"] += pending_eligible + pending_blocked
            result[current]["total"] = result[current]["paid"] + result[current]["pending"]
            current += timedelta(days=1)
        return result

    async def summary(self, period: str, day: date, employee_id: int | None = None, location_id: int | None = None) -> dict:
        start, end = self.bounds(period, day)
        filters = [WorkSessionOrm.work_date.between(start, end), WorkSessionOrm.status == SessionStatus.closed]
        if employee_id:
            filters.append(WorkSessionOrm.employee_id == employee_id)
        if location_id:
            filters.append(WorkSessionOrm.work_location_id == location_id)
        minutes = int(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.minutes), 0)).where(*filters)) or 0)
        production = (await self.session.execute(select(func.coalesce(func.sum(OutputItemOrm.bags), 0),
            func.coalesce(func.sum(OutputItemOrm.kg), 0)).select_from(OutputItemOrm)
            .join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
        if location_id:
            raw = Decimal(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(*filters)) or 0)
            paid = pending = pending_eligible = pending_blocked = needs_review_count = 0
            total = int(raw)
        else:
            salary_days = await self._salary_for_days(start, end, employee_id)
            paid = sum(x["paid"] for x in salary_days.values())
            pending = sum(x["pending"] for x in salary_days.values())
            pending_eligible = sum(x["pending_eligible"] for x in salary_days.values())
            pending_blocked = sum(x["pending_blocked"] for x in salary_days.values())
            needs_review_count = sum(x["needs_review_count"] for x in salary_days.values())
            total = paid + pending
        return {"from": start, "to": end, "minutes": minutes,
                "salary": {"paid": paid, "pending": pending, "pending_eligible": pending_eligible,
                           "pending_blocked": pending_blocked, "needs_review_count": needs_review_count,
                           "total": total},
                "paid": paid, "pending": pending, "pending_eligible": pending_eligible,
                "pending_blocked": pending_blocked, "needs_review_count": needs_review_count,
                "total": total,
                "bags": int(production[0]), "kg": float(production[1])}

    async def products(self, period: str, day: date, employee_id: int | None = None, location_id: int | None = None) -> list[dict]:
        start, end = self.bounds(period, day)
        products = list((await self.session.scalars(select(ProductOrm).order_by(ProductOrm.sort_order))).all())
        result = []
        for product in products:
            filters = [WorkSessionOrm.work_date.between(start, end), OutputItemOrm.product_id == product.id]
            if employee_id:
                filters.append(WorkSessionOrm.employee_id == employee_id)
            if location_id:
                filters.append(WorkSessionOrm.work_location_id == location_id)
            bags, kg = (await self.session.execute(select(
                func.coalesce(func.sum(OutputItemOrm.bags), 0),
                func.coalesce(func.sum(OutputItemOrm.kg), 0),
            ).select_from(OutputItemOrm).join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
            result.append({"code": product.code, "name": product.name, "bags": int(bags), "kg": float(kg)})
        return result

    async def timeseries(self, period: str, day: date, employee_id: int | None = None, location_id: int | None = None) -> list[dict]:
        start, end = self.bounds(period, day)
        salary_days = {} if location_id else await self._salary_for_days(start, end, employee_id)
        rows = []
        current = start
        while current <= end:
            filters = [WorkSessionOrm.work_date == current, WorkSessionOrm.status == SessionStatus.closed]
            if employee_id:
                filters.append(WorkSessionOrm.employee_id == employee_id)
            if location_id:
                filters.append(WorkSessionOrm.work_location_id == location_id)
            minutes = int(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.minutes), 0)).where(*filters)) or 0)
            bags, kg = (await self.session.execute(select(func.coalesce(func.sum(OutputItemOrm.bags), 0),
                func.coalesce(func.sum(OutputItemOrm.kg), 0)).select_from(OutputItemOrm)
                .join(OutputLogOrm).join(WorkSessionOrm).where(*filters))).one()
            if location_id:
                raw = Decimal(await self.session.scalar(select(func.coalesce(func.sum(WorkSessionOrm.amount_raw), 0)).where(*filters)) or 0)
                salary = {"total": int(raw), "paid": 0, "pending": 0, "pending_eligible": 0, "pending_blocked": 0, "needs_review_count": 0}
            else:
                salary = salary_days[current]
            rows.append({"date": current, "minutes": minutes, "salary": salary["total"],
                         "paid": salary["paid"], "pending": salary["pending"],
                         "pending_eligible": salary["pending_eligible"],
                         "pending_blocked": salary["pending_blocked"],
                         "needs_review_count": salary["needs_review_count"],
                         "bags": int(bags), "kg": float(kg)})
            current += timedelta(days=1)
        return rows


class WorkLocationService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    def _validate_location(self, latitude: float, longitude: float, radius_m: int, coordinate_source: str) -> None:
        if not (8 <= latitude <= 24 and 102 <= longitude <= 110):
            raise fail("LOCATION_INVALID", 422)
        if not (30 <= radius_m <= 1000):
            raise fail("LOCATION_INVALID", 422)
        if coordinate_source not in {"device_gps", "manual_coordinates"}:
            raise fail("LOCATION_INVALID", 422)

    async def list_locations(self, active: bool | None = None, q: str | None = None) -> list[dict]:
        query = select(WorkLocationOrm)
        if active is not None:
            query = query.where(WorkLocationOrm.is_active.is_(active))
        if q:
            like = f"%{q.strip()}%"
            query = query.where(or_(WorkLocationOrm.code.ilike(like), WorkLocationOrm.name.ilike(like)))
        rows = (await self.session.scalars(query.order_by(WorkLocationOrm.code))).all()
        return [location_dict(row) for row in rows]

    async def create(
        self,
        actor: EmployeeOrm,
        code: str,
        name: str,
        address: str | None,
        latitude: float,
        longitude: float,
        radius_m: int,
        coordinate_source: str,
        location_accuracy_m: float | None,
        low_accuracy_confirmed: bool = False,
    ) -> dict:
        self._validate_location(latitude, longitude, radius_m, coordinate_source)
        if coordinate_source == "manual_coordinates":
            location_accuracy_m = None
        if coordinate_source == "device_gps" and location_accuracy_m is not None and location_accuracy_m > 100 and not low_accuracy_confirmed:
            raise fail("LOCATION_INVALID", 422, details={"reason": "low_accuracy_requires_confirmation"})
        row = WorkLocationOrm(
            code=code,
            name=name,
            address=address,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            radius_m=radius_m,
            coordinate_source=coordinate_source,
            location_accuracy_m=Decimal(str(location_accuracy_m)) if location_accuracy_m is not None else None,
            is_active=True,
            created_by=actor.id,
        )
        self.session.add(row)
        await self.session.flush()
        if coordinate_source == "device_gps" and location_accuracy_m is not None and location_accuracy_m > 100:
            self.session.add(AuditLogOrm(actor_id=actor.id, action="location_saved_with_low_accuracy",
                                         entity_type="work_location", entity_id=row.id,
                                         new_value={"accuracy_m": location_accuracy_m, "confirmed_by": actor.id,
                                                    "confirmed_at": iso_vn(self.clock.now())}))
        return location_dict(row)

    async def update(self, actor: EmployeeOrm, location_id: int, **values) -> dict:
        row = await self.session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.id == location_id).with_for_update())
        if not row:
            raise fail("LOCATION_NOT_FOUND", 404)
        latitude = float(values.get("latitude", row.latitude))
        longitude = float(values.get("longitude", row.longitude))
        radius_m = int(values.get("radius_m", row.radius_m))
        coordinate_source = values.get("coordinate_source", row.coordinate_source)
        self._validate_location(latitude, longitude, radius_m, coordinate_source)
        old = location_dict(row)
        for field in ["code", "name", "address"]:
            if field in values and values[field] is not None:
                setattr(row, field, values[field])
        row.latitude = Decimal(str(latitude))
        row.longitude = Decimal(str(longitude))
        row.radius_m = radius_m
        row.coordinate_source = coordinate_source
        if coordinate_source == "manual_coordinates":
            row.location_accuracy_m = None
        elif "location_accuracy_m" in values:
            row.location_accuracy_m = Decimal(str(values["location_accuracy_m"])) if values["location_accuracy_m"] is not None else None
        self.session.add(AuditLogOrm(actor_id=actor.id, action="location_updated", entity_type="work_location",
                                     entity_id=row.id, old_value=old, new_value=location_dict(row)))
        return location_dict(row)

    async def set_active(self, actor: EmployeeOrm, location_id: int, active: bool) -> dict:
        row = await self.session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.id == location_id).with_for_update())
        if not row:
            raise fail("LOCATION_NOT_FOUND", 404)
        if not active:
            assignments = int(await self.session.scalar(select(func.count()).select_from(EmployeeLocationAssignmentOrm).where(
                EmployeeLocationAssignmentOrm.location_id == location_id,
                EmployeeLocationAssignmentOrm.effective_to.is_(None),
            )) or 0)
            open_sessions = int(await self.session.scalar(select(func.count()).select_from(WorkSessionOrm).where(
                WorkSessionOrm.work_location_id == location_id,
                WorkSessionOrm.status == SessionStatus.open,
            )) or 0)
            if assignments or open_sessions:
                raise fail("LOCATION_IN_USE", details={"current_assignments": assignments, "open_sessions": open_sessions})
        row.is_active = active
        self.session.add(AuditLogOrm(actor_id=actor.id, action="location_activated" if active else "location_deactivated",
                                     entity_type="work_location", entity_id=row.id))
        return location_dict(row)

    async def assign_employee(self, actor: EmployeeOrm, employee_id: int, location_id: int, reason: str) -> dict:
        if len(reason.strip()) < 5 or len(reason) > 200:
            raise fail("REASON_REQUIRED", 422)
        employee = await self.session.scalar(select(EmployeeOrm).where(EmployeeOrm.id == employee_id).with_for_update())
        if not employee or employee.role != EmployeeRole.employee:
            raise fail("EMPLOYEE_NOT_FOUND", 404)
        current = await current_location_assignment(self.session, employee_id, lock=True)
        location = await self.session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.id == location_id).with_for_update(read=True))
        if not location:
            raise fail("LOCATION_NOT_FOUND", 404)
        if not location.is_active:
            raise fail("LOCATION_INACTIVE")
        now = _vn(self.clock.now())
        if current and current.location_id == location_id:
            return await employee_admin_dict(self.session, employee, now.date())
        old_value = {"location_id": current.location_id if current else None}
        if current:
            current.effective_to = now
        self.session.add(EmployeeLocationAssignmentOrm(employee_id=employee_id, location_id=location_id,
                                                       effective_from=now, changed_by=actor.id, reason=reason))
        self.session.add(AuditLogOrm(actor_id=actor.id, action="employee_location_changed",
                                     entity_type="employee", entity_id=employee_id,
                                     old_value=old_value, new_value={"location_id": location_id}, reason=reason))
        await self.session.flush()
        return await employee_admin_dict(self.session, employee, now.date())


class EmployeeService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session, self.clock = session, clock or Clock()

    async def list_employees(self, q: str | None = None, active: bool | None = None) -> list[dict]:
        query = select(EmployeeOrm).where(EmployeeOrm.role == EmployeeRole.employee)
        if active is not None:
            query = query.where(EmployeeOrm.is_active.is_(active))
        if q:
            like = f"%{q.strip()}%"
            query = query.where(or_(EmployeeOrm.code.ilike(like), EmployeeOrm.full_name.ilike(like)))
        rows = (await self.session.scalars(query.order_by(EmployeeOrm.code))).all()
        return [await employee_admin_dict(self.session, row, _vn(self.clock.now()).date()) for row in rows]

    async def create(self, actor: EmployeeOrm, code: str, name: str, hourly_rate: int, effective_from: date, location_id: int) -> dict:
        employee, invite = await create_employee(self.session, actor, code, name, hourly_rate, effective_from, location_id, self.clock)
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
                          hourly_rate: int, effective_from: date, location_id: int | None = None,
                          clock: Clock | None = None) -> tuple[EmployeeOrm, str]:
    clock = clock or Clock()
    today = _vn(clock.now()).date()
    if effective_from < today or hourly_rate <= 0:
        raise fail("INVALID_EMPLOYEE_DATA", 422)
    if location_id is None:
        location_id = await session.scalar(select(WorkLocationOrm.id).where(WorkLocationOrm.code == "KHO01"))
    location = await session.scalar(select(WorkLocationOrm).where(WorkLocationOrm.id == location_id).with_for_update(read=True))
    if not location:
        raise fail("LOCATION_NOT_FOUND", 404)
    if not location.is_active:
        raise fail("LOCATION_INACTIVE")
    employee = EmployeeOrm(code=code, full_name=name, role=EmployeeRole.employee)
    session.add(employee)
    await session.flush()
    session.add(RateHistoryOrm(employee_id=employee.id, hourly_rate=hourly_rate,
                               effective_from=effective_from, created_by=actor.id))
    session.add(EmployeeLocationAssignmentOrm(employee_id=employee.id, location_id=location.id,
                                             effective_from=clock.now(), changed_by=actor.id,
                                             reason="Phân công khi tạo nhân viên"))
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
            "flag_source": _flag_source(row),
            "check_in_accuracy_m": float(row.check_in_accuracy_m) if row.check_in_accuracy_m is not None else None,
            "check_in_distance_m": float(row.check_in_distance_m),
            "check_out_accuracy_m": float(row.check_out_accuracy_m) if row.check_out_accuracy_m is not None else None,
            "check_out_distance_m": float(row.check_out_distance_m) if row.check_out_distance_m is not None else None,
            "work_location_id": row.work_location_id,
            "location_code": row.location_code_snapshot,
            "location_name": row.location_name_snapshot,
            "location_radius_m": row.location_radius_m_snapshot,
            "nearby_location_id": row.nearby_location_id,
            "nearby_location_distance_m": float(row.nearby_location_distance_m) if row.nearby_location_distance_m is not None else None}
