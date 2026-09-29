from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, DateTime,
    Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text,
    UniqueConstraint, func, text)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from source.enums import EmployeeRole, OutboxStatus, SessionStatus
from .base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmployeeOrm(Base, TimestampMixin):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[EmployeeRole] = mapped_column(Enum(EmployeeRole, native_enum=False), default=EmployeeRole.employee)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class ConsentTextOrm(Base):
    __tablename__ = "consent_texts"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocationConsentOrm(Base):
    __tablename__ = "location_consents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    consent_version: Mapped[int] = mapped_column(ForeignKey("consent_texts.version"))
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InviteCodeOrm(Base):
    __tablename__ = "invite_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RateHistoryOrm(Base):
    __tablename__ = "rate_history"
    __table_args__ = (
        Index("uq_rate_history_employee_effective_active", "employee_id", "effective_from", unique=True,
              postgresql_where=text("cancelled_at IS NULL"), sqlite_where=text("cancelled_at IS NULL")),
        CheckConstraint("hourly_rate > 0"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    hourly_rate: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, default="Dữ liệu trước nâng cấp")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    cancel_reason: Mapped[str | None] = mapped_column(Text)


class ProductOrm(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kg_per_bag: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    sort_order: Mapped[int] = mapped_column(Integer)


class WorkLocationOrm(Base, TimestampMixin):
    __tablename__ = "work_locations"
    __table_args__ = (
        CheckConstraint("latitude >= 8 AND latitude <= 24", name="ck_work_locations_lat_vietnam"),
        CheckConstraint("longitude >= 102 AND longitude <= 110", name="ck_work_locations_lng_vietnam"),
        CheckConstraint("radius_m >= 30 AND radius_m <= 1000", name="ck_work_locations_radius"),
        CheckConstraint("coordinate_source IN ('device_gps', 'manual_coordinates')", name="ck_work_locations_coordinate_source"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    location_type: Mapped[str] = mapped_column(String(32), default="warehouse", server_default=text("'warehouse'"))
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    radius_m: Mapped[int] = mapped_column(Integer)
    coordinate_source: Mapped[str] = mapped_column(String(32))
    location_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))


class EmployeeLocationAssignmentOrm(Base):
    __tablename__ = "employee_location_assignments"
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_employee_location_assignment_time"),
        Index("uq_employee_location_assignment_current", "employee_id", unique=True,
              postgresql_where=text("effective_to IS NULL"), sqlite_where=text("effective_to IS NULL")),
        ExcludeConstraint(
            ("employee_id", "="),
            (text("tstzrange(effective_from, effective_to, '[)')"), "&&"),
            name="ex_employee_location_assignments_no_overlap",
            using="gist",
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("work_locations.id"), index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkSessionOrm(Base, TimestampMixin):
    __tablename__ = "work_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_in_lat: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    check_in_lng: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    check_in_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    check_in_distance_m: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    check_out_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    check_out_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    check_out_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    check_out_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    work_location_id: Mapped[int] = mapped_column(ForeignKey("work_locations.id"), index=True, default=1)
    location_code_snapshot: Mapped[str] = mapped_column(String(32), default="KHO01")
    location_name_snapshot: Mapped[str] = mapped_column(String(200), default="Xưởng chính")
    location_lat_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 7), default=Decimal("10.0"))
    location_lng_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 7), default=Decimal("106.0"))
    location_radius_m_snapshot: Mapped[int] = mapped_column(Integer, default=100)
    flag_source: Mapped[str | None] = mapped_column(String(16))
    nearby_location_id: Mapped[int | None] = mapped_column(ForeignKey("work_locations.id"), index=True)
    nearby_location_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    rate_snapshot: Mapped[int] = mapped_column(Integer)
    minutes: Mapped[int | None] = mapped_column(Integer)
    amount_raw: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus, native_enum=False), index=True)
    review_reason: Mapped[str | None] = mapped_column(String(64))
    flags: Mapped[list[str]] = mapped_column(JsonType, default=list)
    flags_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    flags_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    pay_batch_id: Mapped[int | None] = mapped_column(ForeignKey("pay_batches.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        Index("uq_work_sessions_employee_open", "employee_id", unique=True,
              postgresql_where=text("status = 'open'"), sqlite_where=text("status = 'open'")),
        Index("ix_work_sessions_employee_date", "employee_id", "work_date"),
    )


class OutputLogOrm(Base, TimestampMixin):
    __tablename__ = "output_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_session_id: Mapped[int] = mapped_column(ForeignKey("work_sessions.id", ondelete="CASCADE"), unique=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutputItemOrm(Base):
    __tablename__ = "output_items"
    __table_args__ = (UniqueConstraint("output_log_id", "product_id"), CheckConstraint("bags >= 0"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    output_log_id: Mapped[int] = mapped_column(ForeignKey("output_logs.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    bags: Mapped[int] = mapped_column(Integer)
    kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class PayBatchOrm(Base):
    __tablename__ = "pay_batches"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", "batch_no"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    batch_no: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    day_total_rounded_at_approval: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="paid")
    approved_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLogOrm(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncOutboxOrm(Base):
    __tablename__ = "sync_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus, native_enum=False), default=OutboxStatus.pending, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationOutboxOrm(Base):
    __tablename__ = "notification_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    notification_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus, native_enum=False), default=OutboxStatus.pending, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BotHeartbeatOrm(Base):
    __tablename__ = "bot_heartbeat"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    beat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
