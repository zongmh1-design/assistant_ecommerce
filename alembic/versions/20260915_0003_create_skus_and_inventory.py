"""Create product SKUs, current inventory and inventory movements.

Revision ID: 20260915_0003
Revises: 20260915_0002
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0003"
down_revision: str | Sequence[str] | None = "20260915_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_skus",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=100), nullable=False),
        sa.Column("sku_name", sa.String(length=200), nullable=False),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="product_sku_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("platform_sku_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_skus_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "sku_code",
            name="uq_product_skus_product_code",
        ),
    )
    op.create_index(
        "ix_product_skus_product_id",
        "product_skus",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_skus_status",
        "product_skus",
        ["status"],
        unique=False,
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column(
            "stock_qty",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "locked_qty",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "warning_threshold",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("location_text", sa.String(length=200), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "locked_qty >= 0",
            name="ck_inventory_items_locked_nonnegative",
        ),
        sa.CheckConstraint(
            "locked_qty <= stock_qty",
            name="ck_inventory_items_locked_not_over_stock",
        ),
        sa.CheckConstraint(
            "stock_qty >= 0",
            name="ck_inventory_items_stock_nonnegative",
        ),
        sa.CheckConstraint(
            "warning_threshold >= 0",
            name="ck_inventory_items_warning_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["product_skus.id"],
            name="fk_inventory_items_sku_id_product_skus",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku_id", name="uq_inventory_items_sku_id"),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column(
            "movement_type",
            sa.Enum(
                "initial",
                "inbound",
                "outbound",
                "adjustment",
                name="inventory_movement_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("change_qty", sa.Integer(), nullable=False),
        sa.Column("before_qty", sa.Integer(), nullable=False),
        sa.Column("after_qty", sa.Integer(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "after_qty >= 0",
            name="ck_inventory_movements_after_nonnegative",
        ),
        sa.CheckConstraint(
            "after_qty = before_qty + change_qty",
            name="ck_inventory_movements_quantity_equation",
        ),
        sa.CheckConstraint(
            "before_qty >= 0",
            name="ck_inventory_movements_before_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["product_skus.id"],
            name="fk_inventory_movements_sku_id_product_skus",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_movements_movement_type",
        "inventory_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_sku_id",
        "inventory_movements",
        ["sku_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_sku_id",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_movements_movement_type",
        table_name="inventory_movements",
    )
    op.drop_table("inventory_movements")
    op.drop_table("inventory_items")
    op.drop_index("ix_product_skus_status", table_name="product_skus")
    op.drop_index("ix_product_skus_product_id", table_name="product_skus")
    op.drop_table("product_skus")
