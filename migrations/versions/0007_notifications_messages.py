"""announcements and private messages

Revision ID: 0007_notifications_messages
Revises: 0006_rate_history_timestamptz
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_notifications_messages"
down_revision = "0006_rate_history_timestamptz"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("sender_role", sa.String(16), nullable=False),
        sa.Column("audience_type", sa.String(16), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("work_locations.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_announcements_sender_id", "announcements", ["sender_id"])
    op.create_table(
        "announcement_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("announcement_id", sa.Integer(), sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("announcement_id", "employee_id"),
    )
    op.create_index("ix_announcement_recipients_announcement_id", "announcement_recipients", ["announcement_id"])
    op.create_index("ix_announcement_recipients_employee_id", "announcement_recipients", ["employee_id"])
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.UniqueConstraint("employee_id", "channel"),
    )
    op.create_index("ix_conversations_employee_id", "conversations", ["employee_id"])
    op.create_index("ix_conversations_channel", "conversations", ["channel"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), sa.ForeignKey("announcements.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_by", JSON_TYPE, nullable=True),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_table(
        "message_relays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("chat_id", "telegram_message_id"),
    )
    op.create_index("ix_message_relays_message_id", "message_relays", ["message_id"])
    op.create_index("ix_message_relays_chat_id", "message_relays", ["chat_id"])
    op.create_table(
        "pending_free_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pending_free_messages_employee_id", "pending_free_messages", ["employee_id"])
    op.create_index("ix_pending_free_messages_expires_at", "pending_free_messages", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_free_messages_expires_at", table_name="pending_free_messages")
    op.drop_index("ix_pending_free_messages_employee_id", table_name="pending_free_messages")
    op.drop_table("pending_free_messages")
    op.drop_index("ix_message_relays_chat_id", table_name="message_relays")
    op.drop_index("ix_message_relays_message_id", table_name="message_relays")
    op.drop_table("message_relays")
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_channel", table_name="conversations")
    op.drop_index("ix_conversations_employee_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_announcement_recipients_employee_id", table_name="announcement_recipients")
    op.drop_index("ix_announcement_recipients_announcement_id", table_name="announcement_recipients")
    op.drop_table("announcement_recipients")
    op.drop_index("ix_announcements_sender_id", table_name="announcements")
    op.drop_table("announcements")
