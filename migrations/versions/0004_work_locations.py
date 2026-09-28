"""work locations

Revision ID: 0004_work_locations
Revises: 0003_crv_workforce
Create Date: 2026-09-28 00:00:00.000000
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op


revision = "0004_work_locations"
down_revision = "0003"
branch_labels = None
depends_on = None


def _env_decimal(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    return str(value).strip() or default


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "work_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location_type", sa.String(length=32), server_default="warehouse", nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("coordinate_source", sa.String(length=32), nullable=False),
        sa.Column("location_accuracy_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("latitude >= 8 AND latitude <= 24", name="ck_work_locations_lat_vietnam"),
        sa.CheckConstraint("longitude >= 102 AND longitude <= 110", name="ck_work_locations_lng_vietnam"),
        sa.CheckConstraint("radius_m >= 30 AND radius_m <= 1000", name="ck_work_locations_radius"),
        sa.CheckConstraint("coordinate_source IN ('device_gps', 'manual_coordinates')", name="ck_work_locations_coordinate_source"),
    )
    op.create_index("ix_work_locations_code", "work_locations", ["code"], unique=True)
    op.create_index("ix_work_locations_name", "work_locations", ["name"], unique=True)

    op.create_table(
        "employee_location_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("work_locations.id"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_employee_location_assignment_time"),
    )
    op.create_index("ix_employee_location_assignments_employee_id", "employee_location_assignments", ["employee_id"])
    op.create_index("ix_employee_location_assignments_location_id", "employee_location_assignments", ["location_id"])
    op.create_index("ix_employee_location_assignments_effective_from", "employee_location_assignments", ["effective_from"])
    op.create_index("ix_employee_location_assignments_effective_to", "employee_location_assignments", ["effective_to"])
    op.create_index(
        "uq_employee_location_assignment_current",
        "employee_location_assignments",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
        sqlite_where=sa.text("effective_to IS NULL"),
    )
    if bind.dialect.name == "postgresql":
        op.execute("""
            ALTER TABLE employee_location_assignments
            ADD CONSTRAINT ex_employee_location_assignments_no_overlap
            EXCLUDE USING gist (
                employee_id WITH =,
                tstzrange(effective_from, effective_to, '[)') WITH &&
            )
        """)

    op.add_column("work_sessions", sa.Column("work_location_id", sa.Integer(), nullable=True))
    op.add_column("work_sessions", sa.Column("location_code_snapshot", sa.String(length=32), nullable=True))
    op.add_column("work_sessions", sa.Column("location_name_snapshot", sa.String(length=200), nullable=True))
    op.add_column("work_sessions", sa.Column("location_lat_snapshot", sa.Numeric(10, 7), nullable=True))
    op.add_column("work_sessions", sa.Column("location_lng_snapshot", sa.Numeric(10, 7), nullable=True))
    op.add_column("work_sessions", sa.Column("location_radius_m_snapshot", sa.Integer(), nullable=True))
    op.add_column("work_sessions", sa.Column("flag_source", sa.String(length=16), nullable=True))
    op.add_column("work_sessions", sa.Column("nearby_location_id", sa.Integer(), nullable=True))
    op.add_column("work_sessions", sa.Column("nearby_location_distance_m", sa.Numeric(10, 2), nullable=True))
    op.create_foreign_key("fk_work_sessions_work_location_id", "work_sessions", "work_locations", ["work_location_id"], ["id"])
    op.create_foreign_key("fk_work_sessions_nearby_location_id", "work_sessions", "work_locations", ["nearby_location_id"], ["id"])
    op.create_index("ix_work_sessions_work_location_id", "work_sessions", ["work_location_id"])
    op.create_index("ix_work_sessions_nearby_location_id", "work_sessions", ["nearby_location_id"])

    lat = _env_decimal("WORKSHOP__LAT", "10.0")
    lng = _env_decimal("WORKSHOP__LNG", "106.0")
    radius = int(_env_decimal("WORKSHOP__RADIUS_M", "100"))
    op.execute(sa.text("""
        INSERT INTO work_locations
            (code, name, location_type, latitude, longitude, radius_m, coordinate_source, is_active)
        VALUES
            ('KHO01', 'Xưởng chính', 'warehouse', :lat, :lng, :radius, 'manual_coordinates', true)
        ON CONFLICT (code) DO NOTHING
    """).bindparams(
        sa.bindparam("lat", lat, type_=sa.Numeric(10, 7)),
        sa.bindparam("lng", lng, type_=sa.Numeric(10, 7)),
        sa.bindparam("radius", radius, type_=sa.Integer()),
    ))

    op.execute(sa.text("""
        INSERT INTO employee_location_assignments
            (employee_id, location_id, effective_from, reason)
        SELECT e.id, wl.id, COALESCE(e.created_at, now()), 'Backfill KHO01 từ migration 0004'
        FROM employees e
        CROSS JOIN work_locations wl
        WHERE e.role = 'employee'
          AND wl.code = 'KHO01'
          AND NOT EXISTS (
              SELECT 1 FROM employee_location_assignments a
              WHERE a.employee_id = e.id AND a.effective_to IS NULL
          )
    """))

    op.execute(sa.text("""
        UPDATE work_sessions ws
        SET work_location_id = wl.id,
            location_code_snapshot = wl.code,
            location_name_snapshot = wl.name,
            location_lat_snapshot = wl.latitude,
            location_lng_snapshot = wl.longitude,
            location_radius_m_snapshot = wl.radius_m,
            flag_source = CASE
                WHEN COALESCE(jsonb_exists(ws.flags::jsonb, 'gps_out_of_range'), false)
                  OR COALESCE(jsonb_exists(ws.flags::jsonb, 'gps_low_accuracy'), false)
                THEN
                    CASE
                        WHEN (
                            (ws.check_in_distance_m IS NOT NULL AND ws.check_in_distance_m > wl.radius_m)
                            OR (ws.check_in_accuracy_m IS NOT NULL AND ws.check_in_accuracy_m > 100)
                        )
                        AND (
                            (ws.check_out_distance_m IS NOT NULL AND ws.check_out_distance_m > wl.radius_m)
                            OR (ws.check_out_accuracy_m IS NOT NULL AND ws.check_out_accuracy_m > 100)
                        ) THEN 'both'
                        WHEN (
                            (ws.check_out_distance_m IS NOT NULL AND ws.check_out_distance_m > wl.radius_m)
                            OR (ws.check_out_accuracy_m IS NOT NULL AND ws.check_out_accuracy_m > 100)
                        ) THEN 'check_out'
                        ELSE 'check_in'
                    END
                ELSE NULL
            END
        FROM work_locations wl
        WHERE wl.code = 'KHO01'
          AND ws.work_location_id IS NULL
    """))

    op.alter_column("work_sessions", "work_location_id", nullable=False)
    op.alter_column("work_sessions", "location_code_snapshot", nullable=False)
    op.alter_column("work_sessions", "location_name_snapshot", nullable=False)
    op.alter_column("work_sessions", "location_lat_snapshot", nullable=False)
    op.alter_column("work_sessions", "location_lng_snapshot", nullable=False)
    op.alter_column("work_sessions", "location_radius_m_snapshot", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_work_sessions_nearby_location_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_work_location_id", table_name="work_sessions")
    op.drop_constraint("fk_work_sessions_nearby_location_id", "work_sessions", type_="foreignkey")
    op.drop_constraint("fk_work_sessions_work_location_id", "work_sessions", type_="foreignkey")
    for column in [
        "nearby_location_distance_m",
        "nearby_location_id",
        "flag_source",
        "location_radius_m_snapshot",
        "location_lng_snapshot",
        "location_lat_snapshot",
        "location_name_snapshot",
        "location_code_snapshot",
        "work_location_id",
    ]:
        op.drop_column("work_sessions", column)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE employee_location_assignments DROP CONSTRAINT ex_employee_location_assignments_no_overlap")
    op.drop_index("uq_employee_location_assignment_current", table_name="employee_location_assignments")
    op.drop_index("ix_employee_location_assignments_effective_to", table_name="employee_location_assignments")
    op.drop_index("ix_employee_location_assignments_effective_from", table_name="employee_location_assignments")
    op.drop_index("ix_employee_location_assignments_location_id", table_name="employee_location_assignments")
    op.drop_index("ix_employee_location_assignments_employee_id", table_name="employee_location_assignments")
    op.drop_table("employee_location_assignments")
    op.drop_index("ix_work_locations_name", table_name="work_locations")
    op.drop_index("ix_work_locations_code", table_name="work_locations")
    op.drop_table("work_locations")
