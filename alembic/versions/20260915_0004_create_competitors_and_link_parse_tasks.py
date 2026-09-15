"""Create competitors and public-link parsing tasks.

Revision ID: 20260915_0004
Revises: 20260915_0003
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0004"
down_revision: str | Sequence[str] | None = "20260915_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "taobao", "tmall", "jd", "douyin", "pinduoduo", "other",
                name="competitor_platform_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("sales_hint", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("main_image", sa.String(length=2048), nullable=True),
        sa.Column("selling_points", sa.JSON(), nullable=False),
        sa.Column("review_keywords", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_competitors_product_id_products", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitors_product_id", "competitors", ["product_id"])
    op.create_index("ix_competitors_platform", "competitors", ["platform"])

    op.create_table(
        "public_link_parse_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "task_status",
            sa.Enum(
                "pending", "running", "succeeded", "failed",
                name="public_link_parse_task_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'pending'"), nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("confirmed_competitor_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_public_link_parse_tasks_attempts_nonnegative"),
        sa.ForeignKeyConstraint(
            ["confirmed_competitor_id"], ["competitors.id"],
            name="fk_link_parse_tasks_confirmed_competitor", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_link_parse_tasks_product_id_products", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "confirmed_competitor_id",
            name="uq_public_link_parse_tasks_confirmed_competitor_id",
        ),
    )
    op.create_index(
        "ix_public_link_parse_tasks_product_id", "public_link_parse_tasks", ["product_id"]
    )
    op.create_index(
        "ix_public_link_parse_tasks_task_status", "public_link_parse_tasks", ["task_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_public_link_parse_tasks_task_status", table_name="public_link_parse_tasks")
    op.drop_index("ix_public_link_parse_tasks_product_id", table_name="public_link_parse_tasks")
    op.drop_table("public_link_parse_tasks")
    op.drop_index("ix_competitors_platform", table_name="competitors")
    op.drop_index("ix_competitors_product_id", table_name="competitors")
    op.drop_table("competitors")
