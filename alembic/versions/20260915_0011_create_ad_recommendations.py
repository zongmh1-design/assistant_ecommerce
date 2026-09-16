"""Create historical, human-decided advertising recommendations.

Revision ID: 20260915_0011
Revises: 20260915_0010
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0011"
down_revision: str | Sequence[str] | None = "20260915_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ad_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("objective_text", sa.Text(), nullable=False),
        sa.Column("audience_segments_json", sa.JSON(), nullable=False),
        sa.Column("budget_plan_json", sa.JSON(), nullable=False),
        sa.Column("creative_tests_json", sa.JSON(), nullable=False),
        sa.Column("bid_strategy_json", sa.JSON(), nullable=False),
        sa.Column("risk_controls_json", sa.JSON(), nullable=False),
        sa.Column("next_steps_json", sa.JSON(), nullable=False),
        sa.Column(
            "confirm_status",
            sa.Enum(
                "pending", "confirmed", "rejected",
                name="ad_recommendation_confirm_status",
                native_enum=False, create_constraint=True,
            ),
            server_default=sa.text("'pending'"), nullable=False,
        ),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirm_remark", sa.Text(), nullable=True),
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
            name="fk_ad_recommendations_product_id_products", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"], ["users.id"],
            name="fk_ad_recommendations_confirmed_by_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_recommendations_product_id", "ad_recommendations", ["product_id"])
    op.create_index("ix_ad_recommendations_confirm_status", "ad_recommendations", ["confirm_status"])
    op.create_index("ix_ad_recommendations_created_at", "ad_recommendations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ad_recommendations_created_at", table_name="ad_recommendations")
    op.drop_index("ix_ad_recommendations_confirm_status", table_name="ad_recommendations")
    op.drop_index("ix_ad_recommendations_product_id", table_name="ad_recommendations")
    op.drop_table("ad_recommendations")
