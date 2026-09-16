"""Create unified main-image and video-script creative plans.

Revision ID: 20260915_0007
Revises: 20260915_0006
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0007"
down_revision: str | Sequence[str] | None = "20260915_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creative_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "plan_type",
            sa.Enum(
                "main_image", "video_script",
                name="creative_plan_type", native_enum=False, create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("rationale_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "selected", "archived",
                name="creative_plan_status", native_enum=False, create_constraint=True,
            ),
            server_default=sa.text("'draft'"), nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("usage_json", sa.JSON(), nullable=True),
        sa.Column("input_context_json", sa.JSON(), nullable=False),
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
            name="fk_creative_plans_product_id_products", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_plans_product_id", "creative_plans", ["product_id"])
    op.create_index("ix_creative_plans_plan_type", "creative_plans", ["plan_type"])
    op.create_index("ix_creative_plans_status", "creative_plans", ["status"])
    op.create_index(
        "uq_creative_plans_selected_product_type",
        "creative_plans",
        ["product_id", "plan_type"],
        unique=True,
        postgresql_where=sa.text("status = 'selected'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_creative_plans_selected_product_type", table_name="creative_plans"
    )
    op.drop_index("ix_creative_plans_status", table_name="creative_plans")
    op.drop_index("ix_creative_plans_plan_type", table_name="creative_plans")
    op.drop_index("ix_creative_plans_product_id", table_name="creative_plans")
    op.drop_table("creative_plans")
