"""Create stores and products tables.

Revision ID: 20260915_0002
Revises: 20260915_0001
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0002"
down_revision: str | Sequence[str] | None = "20260915_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_name", sa.String(length=100), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "taobao",
                "tmall",
                "jd",
                "douyin",
                "pinduoduo",
                "other",
                name="platform_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("external_store_id", sa.String(length=100), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stores_platform", "stores", ["platform"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "taobao",
                "tmall",
                "jd",
                "douyin",
                "pinduoduo",
                "other",
                name="product_platform_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("selling_points", sa.JSON(), nullable=False),
        sa.Column("product_url", sa.String(length=2048), nullable=True),
        sa.Column("images_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "inactive",
                name="product_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
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
            ["store_id"],
            ["stores.id"],
            name="fk_products_store_id_stores",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_platform", "products", ["platform"], unique=False)
    op.create_index("ix_products_status", "products", ["status"], unique=False)
    op.create_index("ix_products_store_id", "products", ["store_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_store_id", table_name="products")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_index("ix_products_platform", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_stores_platform", table_name="stores")
    op.drop_table("stores")
