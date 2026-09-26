"""Create CRV workforce schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

jsonb = postgresql.JSONB(astext_type=sa.Text())


def timestamp(nullable: bool = False) -> sa.DateTime:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.Enum("employee", "manager", "director", native_enum=False), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_employees_code", "employees", ["code"], unique=True)
    op.create_index("ix_employees_telegram_id", "employees", ["telegram_id"], unique=True)

    op.create_table(
        "consent_texts",
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("effective_at", timestamp(), nullable=False),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_consent_texts_effective_at", "consent_texts", ["effective_at"])

    op.create_table(
        "location_consents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_version", sa.Integer(), sa.ForeignKey("consent_texts.version"), nullable=False),
        sa.Column("consented_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("withdrawn_at", timestamp(), nullable=True),
    )
    op.create_index("ix_location_consents_employee_id", "location_consents", ["employee_id"])

    op.create_table(
        "invite_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("used_at", timestamp(), nullable=True),
        sa.Column("expires_at", timestamp(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_invite_codes_employee_id", "invite_codes", ["employee_id"])
    op.create_index("ix_invite_codes_code", "invite_codes", ["code"], unique=True)
    op.create_index("ix_invite_codes_expires_at", "invite_codes", ["expires_at"])

    op.create_table(
        "rate_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hourly_rate", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("hourly_rate > 0"),
        sa.UniqueConstraint("employee_id", "effective_from"),
    )
    op.create_index("ix_rate_history_employee_id", "rate_history", ["employee_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kg_per_bag", sa.Numeric(6, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "pay_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("batch_no", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("day_total_rounded_at_approval", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("approved_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "work_date", "batch_no"),
    )
    op.create_index("ix_pay_batches_employee_id", "pay_batches", ["employee_id"])
    op.create_index("ix_pay_batches_work_date", "pay_batches", ["work_date"])

    op.create_table(
        "work_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in_at", timestamp(), nullable=False),
        sa.Column("check_out_at", timestamp(), nullable=True),
        sa.Column("check_in_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("check_in_lng", sa.Numeric(10, 7), nullable=False),
        sa.Column("check_in_accuracy_m", sa.Numeric(10, 2), nullable=False),
        sa.Column("check_in_distance_m", sa.Numeric(10, 2), nullable=False),
        sa.Column("check_out_lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("check_out_lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("check_out_accuracy_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("check_out_distance_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("rate_snapshot", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("amount_raw", sa.Numeric(14, 4), nullable=True),
        sa.Column("status", sa.Enum("open", "closed", "needs_review", native_enum=False), nullable=False),
        sa.Column("review_reason", sa.String(length=64), nullable=True),
        sa.Column("flags", jsonb, nullable=False),
        sa.Column("flags_reviewed_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("flags_reviewed_at", timestamp(), nullable=True),
        sa.Column("closed_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("pay_batch_id", sa.Integer(), sa.ForeignKey("pay_batches.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_work_sessions_employee_id", "work_sessions", ["employee_id"])
    op.create_index("ix_work_sessions_work_date", "work_sessions", ["work_date"])
    op.create_index("ix_work_sessions_status", "work_sessions", ["status"])
    op.create_index("ix_work_sessions_pay_batch_id", "work_sessions", ["pay_batch_id"])
    op.create_index("ix_work_sessions_employee_date", "work_sessions", ["employee_id", "work_date"])
    op.create_index(
        "uq_work_sessions_employee_open",
        "work_sessions",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "output_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_session_id", sa.Integer(), sa.ForeignKey("work_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_at", timestamp(), nullable=True),
        sa.Column("locked_at", timestamp(), nullable=False),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("work_session_id"),
    )

    op.create_table(
        "output_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("output_log_id", sa.Integer(), sa.ForeignKey("output_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("bags", sa.Integer(), nullable=False),
        sa.Column("kg", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("bags >= 0"),
        sa.UniqueConstraint("output_log_id", "product_id"),
    )
    op.create_index("ix_output_items_output_log_id", "output_items", ["output_log_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("old_value", jsonb, nullable=True),
        sa.Column("new_value", jsonb, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "sync_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", jsonb, nullable=False),
        sa.Column("status", sa.Enum("pending", "sent", "failed", native_enum=False), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", timestamp(), nullable=True),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", timestamp(), nullable=True),
    )
    op.create_index("ix_sync_outbox_event_type", "sync_outbox", ["event_type"])
    op.create_index("ix_sync_outbox_status", "sync_outbox", ["status"])

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("payload", jsonb, nullable=False),
        sa.Column("status", sa.Enum("pending", "sent", "failed", native_enum=False), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", timestamp(), nullable=True),
        sa.Column("created_at", timestamp(), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", timestamp(), nullable=True),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_notification_outbox_chat_id", "notification_outbox", ["chat_id"])
    op.create_index("ix_notification_outbox_status", "notification_outbox", ["status"])

    op.create_table(
        "bot_heartbeat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("beat_at", timestamp(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bot_heartbeat")
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_chat_id", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_sync_outbox_status", table_name="sync_outbox")
    op.drop_index("ix_sync_outbox_event_type", table_name="sync_outbox")
    op.drop_table("sync_outbox")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_output_items_output_log_id", table_name="output_items")
    op.drop_table("output_items")
    op.drop_table("output_logs")
    op.drop_index("uq_work_sessions_employee_open", table_name="work_sessions")
    op.drop_index("ix_work_sessions_employee_date", table_name="work_sessions")
    op.drop_index("ix_work_sessions_pay_batch_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_status", table_name="work_sessions")
    op.drop_index("ix_work_sessions_work_date", table_name="work_sessions")
    op.drop_index("ix_work_sessions_employee_id", table_name="work_sessions")
    op.drop_table("work_sessions")
    op.drop_index("ix_pay_batches_work_date", table_name="pay_batches")
    op.drop_index("ix_pay_batches_employee_id", table_name="pay_batches")
    op.drop_table("pay_batches")
    op.drop_table("products")
    op.drop_index("ix_rate_history_employee_id", table_name="rate_history")
    op.drop_table("rate_history")
    op.drop_index("ix_invite_codes_expires_at", table_name="invite_codes")
    op.drop_index("ix_invite_codes_code", table_name="invite_codes")
    op.drop_index("ix_invite_codes_employee_id", table_name="invite_codes")
    op.drop_table("invite_codes")
    op.drop_index("ix_location_consents_employee_id", table_name="location_consents")
    op.drop_table("location_consents")
    op.drop_index("ix_consent_texts_effective_at", table_name="consent_texts")
    op.drop_table("consent_texts")
    op.drop_index("ix_employees_telegram_id", table_name="employees")
    op.drop_index("ix_employees_code", table_name="employees")
    op.drop_table("employees")
