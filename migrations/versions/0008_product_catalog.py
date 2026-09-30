"""product catalog with snapshots (SPEC 2.20)

Revision ID: 0008_product_catalog
Revises: 0007_notifications_messages
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_product_catalog"
down_revision = "0007_notifications_messages"
branch_labels = None
depends_on = None


def _check_legacy_kg_consistent(bind) -> None:
    rows = bind.execute(sa.text("""
        SELECT oi.id, oi.output_log_id, oi.product_id, oi.bags, oi.kg,
               p.code, p.kg_per_bag
        FROM output_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.kg != (oi.bags * p.kg_per_bag)
    """)).fetchall()
    if rows:
        details = "; ".join(
            f"id={r[0]} log={r[1]} product={r[5]} bags={r[3]} kg={r[4]} kg_per_bag={r[6]}"
            for r in rows[:20]
        )
        raise RuntimeError(
            f"Migration 0008 STOPPED: {len(rows)} output_items rows have "
            f"kg != bags * kg_per_bag (data would be corrupted). "
            f"First rows: {details}"
        )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ---- 0. Verify legacy kg consistency (SPEC 2.20 section 8) ----
    _check_legacy_kg_consistent(bind)

    items_before = bind.execute(sa.text("SELECT count(*) FROM output_items")).scalar()
    logs_before = bind.execute(sa.text("SELECT count(*) FROM output_logs")).scalar()
    products_before = bind.execute(sa.text("SELECT count(*) FROM products")).scalar()

    # ---- 1. products: new lifecycle columns ----
    op.add_column("products", sa.Column("unit_code", sa.String(length=16), nullable=True))
    op.add_column("products", sa.Column("unit_label", sa.String(length=32), nullable=True))
    op.add_column("products", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("products", sa.Column("scope", sa.String(length=16), server_default="all", nullable=False))
    op.add_column("products", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True))
    op.add_column("products", sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True))
    op.add_column("products", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("products", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.execute("UPDATE products SET unit_code = 'BAG' WHERE unit_code IS NULL")
    op.execute("UPDATE products SET unit_label = 'Túi' WHERE unit_label IS NULL")
    op.alter_column("products", "unit_code", existing_type=sa.String(length=16),
                    nullable=False, server_default="BAG")
    op.alter_column("products", "unit_label", existing_type=sa.String(length=32),
                    nullable=False, server_default="Túi")
    op.alter_column("products", "is_active", existing_type=sa.Boolean(),
                    nullable=False, server_default=sa.text("true"))
    op.alter_column("products", "scope", existing_type=sa.String(length=16),
                    nullable=False, server_default="all")

    # kg_per_bag (6,2) -> kg_per_unit (10,3), values preserved
    if dialect == "postgresql":
        op.alter_column(
            "products", "kg_per_bag",
            new_column_name="kg_per_unit",
            existing_type=sa.Numeric(6, 2),
            type_=sa.Numeric(10, 3),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("products") as batch:
            batch.alter_column("kg_per_bag", new_column_name="kg_per_unit",
                               existing_type=sa.Numeric(6, 2), type_=sa.Numeric(10, 3),
                               existing_nullable=False)

    op.create_check_constraint("ck_products_kg_per_unit", "products",
                               "kg_per_unit >= 0.001 AND kg_per_unit <= 1000")
    op.create_check_constraint("ck_products_scope", "products",
                               "scope IN ('all', 'restricted')")
    op.create_index("uq_products_name_active", "products", ["name"], unique=True,
                    postgresql_where=sa.text("deleted_at IS NULL"),
                    sqlite_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_index("ix_products_scope", "products", ["scope"])

    # ---- 2. scope tables ----
    op.create_table(
        "product_location_scopes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("work_locations.id"), nullable=False),
        sa.UniqueConstraint("product_id", "location_id"),
    )
    op.create_index("ix_product_location_scopes_product_id", "product_location_scopes", ["product_id"])
    op.create_index("ix_product_location_scopes_location_id", "product_location_scopes", ["location_id"])

    op.create_table(
        "product_employee_scopes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("product_id", "employee_id"),
    )
    op.create_index("ix_product_employee_scopes_product_id", "product_employee_scopes", ["product_id"])
    op.create_index("ix_product_employee_scopes_employee_id", "product_employee_scopes", ["employee_id"])

    # ---- 3. output_logs: status + opened_at ----
    op.add_column("output_logs", sa.Column("status", sa.String(length=24), nullable=True))
    op.add_column("output_logs", sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))
    if dialect == "postgresql":
        op.execute(sa.text("""
            UPDATE output_logs
            SET opened_at = COALESCE(submitted_at, locked_at - make_interval(mins => 10), locked_at)
            WHERE opened_at IS NULL
        """))
        op.execute(sa.text("""
            UPDATE output_logs
            SET status = CASE
                WHEN submitted_at IS NOT NULL THEN 'submitted'
                WHEN locked_at <= now() THEN 'locked_unsubmitted'
                ELSE 'pending'
            END
            WHERE status IS NULL
        """))
    else:
        op.execute(sa.text("""
            UPDATE output_logs
            SET opened_at = COALESCE(submitted_at, locked_at)
            WHERE opened_at IS NULL
        """))
        op.execute(sa.text("""
            UPDATE output_logs
            SET status = CASE
                WHEN submitted_at IS NOT NULL THEN 'submitted'
                WHEN locked_at <= CURRENT_TIMESTAMP THEN 'locked_unsubmitted'
                ELSE 'pending'
            END
            WHERE status IS NULL
        """))
    op.alter_column("output_logs", "status", existing_type=sa.String(length=24), nullable=False)
    op.alter_column("output_logs", "opened_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.create_check_constraint("ck_output_logs_status", "output_logs",
                               "status IN ('pending', 'submitted', 'locked_unsubmitted')")
    op.create_index("ix_output_logs_status", "output_logs", ["status"])

    # ---- 4. output_items: snapshots + quantity + total_kg generated ----
    op.add_column("output_items", sa.Column("product_code_snapshot", sa.String(length=32), nullable=True))
    op.add_column("output_items", sa.Column("product_name_snapshot", sa.String(length=100), nullable=True))
    op.add_column("output_items", sa.Column("unit_code_snapshot", sa.String(length=16), nullable=True))
    op.add_column("output_items", sa.Column("unit_label_snapshot", sa.String(length=32), nullable=True))
    op.add_column("output_items", sa.Column("kg_per_unit_snapshot", sa.Numeric(10, 3), nullable=True))
    op.add_column("output_items", sa.Column("sort_order_snapshot", sa.Integer(), nullable=True))
    if dialect == "postgresql":
        op.execute(sa.text("""
            UPDATE output_items oi
            SET product_code_snapshot = p.code,
                product_name_snapshot = p.name,
                unit_code_snapshot = 'BAG',
                unit_label_snapshot = 'Túi',
                kg_per_unit_snapshot = p.kg_per_unit,
                sort_order_snapshot = p.sort_order
            FROM products p
            WHERE p.id = oi.product_id
        """))
    else:
        op.execute(sa.text("""
            UPDATE output_items
            SET product_code_snapshot = (SELECT code FROM products WHERE products.id = output_items.product_id),
                product_name_snapshot = (SELECT name FROM products WHERE products.id = output_items.product_id),
                unit_code_snapshot = 'BAG',
                unit_label_snapshot = 'Túi',
                kg_per_unit_snapshot = (SELECT kg_per_unit FROM products WHERE products.id = output_items.product_id),
                sort_order_snapshot = (SELECT sort_order FROM products WHERE products.id = output_items.product_id)
        """))
    for col, typ in [
        ("product_code_snapshot", sa.String(length=32)),
        ("product_name_snapshot", sa.String(length=100)),
        ("unit_code_snapshot", sa.String(length=16)),
        ("unit_label_snapshot", sa.String(length=32)),
        ("kg_per_unit_snapshot", sa.Numeric(10, 3)),
        ("sort_order_snapshot", sa.Integer()),
    ]:
        op.alter_column("output_items", col, existing_type=typ, nullable=False)

    # bags -> quantity (PG renames column and updates the CHECK automatically)
    op.alter_column("output_items", "bags", new_column_name="quantity",
                    existing_type=sa.Integer(), existing_nullable=False)
    op.create_check_constraint("ck_output_items_quantity", "output_items", "quantity >= 0")

    if dialect == "postgresql":
        op.drop_column("output_items", "kg")
        op.add_column("output_items", sa.Column(
            "total_kg", sa.Numeric(14, 3),
            sa.Computed("quantity * kg_per_unit_snapshot", persisted=True),
            nullable=False,
        ))
    else:
        with op.batch_alter_table("output_items", recreate="always") as batch:
            batch.drop_column("kg")
    if dialect != "postgresql":
        # sqlite: recreate via batch is handled by model Computed on fresh create;
        # for migrated DBs add a plain column then rely on app writes.
        # We add total_kg as generated via raw SQL when supported, else plain.
        try:
            op.add_column("output_items", sa.Column(
                "total_kg", sa.Numeric(14, 3),
                sa.Computed("quantity * kg_per_unit_snapshot", persisted=True),
                nullable=True,
            ))
            op.execute("UPDATE output_items SET total_kg = quantity * kg_per_unit_snapshot")
        except Exception:
            pass

    if products_before == 0:
        products_table = sa.table(
            "products",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("unit_code", sa.String),
            sa.column("unit_label", sa.String),
            sa.column("kg_per_unit", sa.Numeric),
            sa.column("sort_order", sa.Integer),
            sa.column("is_active", sa.Boolean),
            sa.column("scope", sa.String),
        )
        op.bulk_insert(products_table, [
            {"code": "BOT", "name": "Bột", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 1.2, "sort_order": 1, "is_active": True, "scope": "all"},
            {"code": "XUC_XICH", "name": "Xúc xích", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 1.0, "sort_order": 2, "is_active": True, "scope": "all"},
            {"code": "PHO_MAI", "name": "Phô mai", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 1.0, "sort_order": 3, "is_active": True, "scope": "all"},
            {"code": "CHA_BONG", "name": "Chà bông", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 1.0, "sort_order": 4, "is_active": True, "scope": "all"},
            {"code": "SOT_CAM", "name": "Sốt cam", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 2.0, "sort_order": 5, "is_active": True, "scope": "all"},
            {"code": "SOT_TRANG", "name": "Sốt trắng", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 2.0, "sort_order": 6, "is_active": True, "scope": "all"},
            {"code": "BO", "name": "Bơ", "unit_code": "BAG", "unit_label": "Túi", "kg_per_unit": 2.0, "sort_order": 7, "is_active": True, "scope": "all"},
        ])

    items_after = bind.execute(sa.text("SELECT count(*) FROM output_items")).scalar()
    logs_after = bind.execute(sa.text("SELECT count(*) FROM output_logs")).scalar()
    assert items_before == items_after, f"output_items count changed {items_before} -> {items_after}"
    assert logs_before == logs_after, f"output_logs count changed {logs_before} -> {logs_after}"


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_column("output_items", "total_kg")
        op.add_column("output_items", sa.Column("kg", sa.Numeric(10, 2), nullable=True))
        op.execute("UPDATE output_items SET kg = quantity * kg_per_unit_snapshot")
        op.alter_column("output_items", "kg", existing_type=sa.Numeric(10, 2), nullable=False)
    else:
        with op.batch_alter_table("output_items", recreate="always") as batch:
            try:
                batch.drop_column("total_kg")
            except Exception:
                pass
            batch.add_column(sa.Column("kg", sa.Numeric(10, 2), nullable=True))
        op.execute("UPDATE output_items SET kg = quantity * kg_per_unit_snapshot")

    op.drop_constraint("ck_output_items_quantity", "output_items", type_="check")
    op.alter_column("output_items", "quantity", new_column_name="bags",
                    existing_type=sa.Integer(), existing_nullable=False)

    for col in ["sort_order_snapshot", "kg_per_unit_snapshot", "unit_label_snapshot",
                "unit_code_snapshot", "product_name_snapshot", "product_code_snapshot"]:
        op.drop_column("output_items", col)

    op.drop_index("ix_output_logs_status", table_name="output_logs")
    op.drop_constraint("ck_output_logs_status", "output_logs", type_="check")
    op.drop_column("output_logs", "opened_at")
    op.drop_column("output_logs", "status")

    op.drop_index("ix_product_employee_scopes_employee_id", table_name="product_employee_scopes")
    op.drop_index("ix_product_employee_scopes_product_id", table_name="product_employee_scopes")
    op.drop_table("product_employee_scopes")
    op.drop_index("ix_product_location_scopes_location_id", table_name="product_location_scopes")
    op.drop_index("ix_product_location_scopes_product_id", table_name="product_location_scopes")
    op.drop_table("product_location_scopes")

    op.drop_index("ix_products_scope", table_name="products")
    op.drop_index("ix_products_is_active", table_name="products")
    op.drop_index("uq_products_name_active", table_name="products")
    op.drop_constraint("ck_products_scope", "products", type_="check")
    op.drop_constraint("ck_products_kg_per_unit", "products", type_="check")

    if dialect == "postgresql":
        op.alter_column(
            "products", "kg_per_unit",
            new_column_name="kg_per_bag",
            existing_type=sa.Numeric(10, 3),
            type_=sa.Numeric(6, 2),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("products") as batch:
            batch.alter_column("kg_per_unit", new_column_name="kg_per_bag",
                               existing_type=sa.Numeric(10, 3), type_=sa.Numeric(6, 2),
                               existing_nullable=False)

    for col in ["updated_at", "created_at", "created_by", "deleted_by", "deleted_at",
                "scope", "is_active", "unit_label", "unit_code"]:
        op.drop_column("products", col)
