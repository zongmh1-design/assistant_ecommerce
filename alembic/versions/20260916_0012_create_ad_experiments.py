"""Create human-controlled advertising experiment plans.

Revision ID: 20260916_0012
Revises: 20260915_0011
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0012"
down_revision: str | Sequence[str] | None = "20260915_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ad_experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("ad_recommendation_id", sa.Integer(), nullable=False),
        sa.Column("related_asset_id", sa.Integer(), nullable=True),
        sa.Column("related_link_id", sa.Integer(), nullable=True),
        sa.Column("experiment_name", sa.String(length=200), nullable=False),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column("audience_text", sa.Text(), nullable=False),
        sa.Column("budget_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("success_metric_text", sa.Text(), nullable=False),
        sa.Column("hypothesis_text", sa.Text(), nullable=False),
        sa.Column(
            "experiment_status",
            sa.Enum(
                "draft", "confirmed", "running", "finished", "cancelled",
                name="ad_experiment_status", native_enum=False, create_constraint=True,
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
        sa.CheckConstraint("budget_amount > 0", name="ck_ad_experiments_budget_positive"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_ad_experiments_product_id_products", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ad_recommendation_id"], ["ad_recommendations.id"],
            name="fk_ad_experiments_recommendation_id_ad_recommendations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["related_asset_id"], ["generated_assets.id"],
            name="fk_ad_experiments_related_asset_id_generated_assets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["related_link_id"], ["promotion_links.id"],
            name="fk_ad_experiments_related_link_id_promotion_links",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_experiments_product_id", "ad_experiments", ["product_id"])
    op.create_index("ix_ad_experiments_ad_recommendation_id", "ad_experiments", ["ad_recommendation_id"])
    op.create_index("ix_ad_experiments_experiment_status", "ad_experiments", ["experiment_status"])
    op.create_index("ix_ad_experiments_created_at", "ad_experiments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ad_experiments_created_at", table_name="ad_experiments")
    op.drop_index("ix_ad_experiments_experiment_status", table_name="ad_experiments")
    op.drop_index("ix_ad_experiments_ad_recommendation_id", table_name="ad_experiments")
    op.drop_index("ix_ad_experiments_product_id", table_name="ad_experiments")
    op.drop_table("ad_experiments")
