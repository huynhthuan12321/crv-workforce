"""rate history by timestamp

Revision ID: 0006_rate_history_timestamptz
Revises: 0005_nullable_gps_accuracy
Create Date: 2026-09-28 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_rate_history_timestamptz"
down_revision = "0005_nullable_gps_accuracy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_constraint("rate_history_employee_id_effective_from_key", "rate_history", type_="unique")
        op.alter_column(
            "rate_history",
            "effective_from",
            existing_type=sa.Date(),
            type_=sa.DateTime(timezone=True),
            postgresql_using="(effective_from::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')",
            existing_nullable=False,
        )
        op.add_column("rate_history", sa.Column("reason", sa.Text(), nullable=True))
        op.execute("UPDATE rate_history SET reason = 'Dữ liệu trước nâng cấp' WHERE reason IS NULL")
        op.alter_column("rate_history", "reason", existing_type=sa.Text(), nullable=False)
        op.add_column("rate_history", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("rate_history", sa.Column("cancelled_by", sa.Integer(), nullable=True))
        op.add_column("rate_history", sa.Column("cancel_reason", sa.Text(), nullable=True))
        op.create_foreign_key("fk_rate_history_cancelled_by_employees", "rate_history", "employees", ["cancelled_by"], ["id"])
        op.create_index(
            "uq_rate_history_employee_effective_active",
            "rate_history",
            ["employee_id", "effective_from"],
            unique=True,
            postgresql_where=sa.text("cancelled_at IS NULL"),
        )
    else:
        with op.batch_alter_table("rate_history") as batch:
            batch.drop_constraint("rate_history_employee_id_effective_from_key", type_="unique")
            batch.alter_column("effective_from", existing_type=sa.Date(), type_=sa.DateTime(timezone=True), existing_nullable=False)
            batch.add_column(sa.Column("reason", sa.Text(), nullable=True))
            batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(sa.Column("cancelled_by", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("cancel_reason", sa.Text(), nullable=True))
            batch.create_foreign_key("fk_rate_history_cancelled_by_employees", "employees", ["cancelled_by"], ["id"])
        op.execute("UPDATE rate_history SET reason = 'Dữ liệu trước nâng cấp' WHERE reason IS NULL")
        with op.batch_alter_table("rate_history") as batch:
            batch.alter_column("reason", existing_type=sa.Text(), nullable=False)
            batch.create_index(
                "uq_rate_history_employee_effective_active",
                ["employee_id", "effective_from"],
                unique=True,
                sqlite_where=sa.text("cancelled_at IS NULL"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_index("uq_rate_history_employee_effective_active", table_name="rate_history", postgresql_where=sa.text("cancelled_at IS NULL"))
        op.drop_constraint("fk_rate_history_cancelled_by_employees", "rate_history", type_="foreignkey")
        op.drop_column("rate_history", "cancel_reason")
        op.drop_column("rate_history", "cancelled_by")
        op.drop_column("rate_history", "cancelled_at")
        op.drop_column("rate_history", "reason")
        op.alter_column(
            "rate_history",
            "effective_from",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.Date(),
            postgresql_using="(effective_from AT TIME ZONE 'Asia/Ho_Chi_Minh')::date",
            existing_nullable=False,
        )
        op.create_unique_constraint("rate_history_employee_id_effective_from_key", "rate_history", ["employee_id", "effective_from"])
    else:
        with op.batch_alter_table("rate_history") as batch:
            batch.drop_index("uq_rate_history_employee_effective_active")
            batch.drop_constraint("fk_rate_history_cancelled_by_employees", type_="foreignkey")
            batch.drop_column("cancel_reason")
            batch.drop_column("cancelled_by")
            batch.drop_column("cancelled_at")
            batch.drop_column("reason")
            batch.alter_column("effective_from", existing_type=sa.DateTime(timezone=True), type_=sa.Date(), existing_nullable=False)
            batch.create_unique_constraint("rate_history_employee_id_effective_from_key", ["employee_id", "effective_from"])
