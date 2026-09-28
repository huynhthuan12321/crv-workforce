"""allow unknown gps accuracy

Revision ID: 0005_nullable_gps_accuracy
Revises: 0004_work_locations
Create Date: 2026-09-28 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_nullable_gps_accuracy"
down_revision = "0004_work_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "work_sessions",
        "check_in_accuracy_m",
        existing_type=sa.Numeric(10, 2),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE work_sessions SET check_in_accuracy_m = 0 WHERE check_in_accuracy_m IS NULL")
    op.alter_column(
        "work_sessions",
        "check_in_accuracy_m",
        existing_type=sa.Numeric(10, 2),
        nullable=False,
    )
