"""Create manually entered performance records with derived metrics.

Revision ID: 20260916_0013
Revises: 20260916_0012
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0013"
down_revision: str | Sequence[str] | None = "20260916_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "performance_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("creative_plan_id", sa.Integer(), nullable=True),
        sa.Column("generated_asset_id", sa.Integer(), nullable=True),
        sa.Column("promotion_link_id", sa.Integer(), nullable=True),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("ctr", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("spend", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("roi", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("period_end > period_start", name="ck_performance_records_period_order"),
        sa.CheckConstraint("impressions >= 0", name="ck_performance_records_impressions_nonnegative"),
        sa.CheckConstraint("clicks >= 0", name="ck_performance_records_clicks_nonnegative"),
        sa.CheckConstraint("conversions >= 0", name="ck_performance_records_conversions_nonnegative"),
        sa.CheckConstraint("clicks <= impressions", name="ck_performance_records_clicks_within_impressions"),
        sa.CheckConstraint("conversions <= clicks", name="ck_performance_records_conversions_within_clicks"),
        sa.CheckConstraint("spend >= 0", name="ck_performance_records_spend_nonnegative"),
        sa.CheckConstraint("revenue >= 0", name="ck_performance_records_revenue_nonnegative"),
        sa.CheckConstraint("ctr >= 0 AND ctr <= 1", name="ck_performance_records_ctr_range"),
        sa.CheckConstraint(
            "conversion_rate >= 0 AND conversion_rate <= 1",
            name="ck_performance_records_conversion_rate_range",
        ),
        sa.CheckConstraint(
            "(spend = 0 AND roi IS NULL) OR (spend > 0 AND roi IS NOT NULL)",
            name="ck_performance_records_roi_defined_by_spend",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["creative_plan_id"], ["creative_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_asset_id"], ["generated_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["promotion_link_id"], ["promotion_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["experiment_id"], ["ad_experiments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_performance_records_product_id", "performance_records", ["product_id"])
    op.create_index("ix_performance_records_generated_asset_id", "performance_records", ["generated_asset_id"])
    op.create_index("ix_performance_records_promotion_link_id", "performance_records", ["promotion_link_id"])
    op.create_index("ix_performance_records_experiment_id", "performance_records", ["experiment_id"])
    op.create_index("ix_performance_records_period_start", "performance_records", ["period_start"])


def downgrade() -> None:
    op.drop_index("ix_performance_records_period_start", table_name="performance_records")
    op.drop_index("ix_performance_records_experiment_id", table_name="performance_records")
    op.drop_index("ix_performance_records_promotion_link_id", table_name="performance_records")
    op.drop_index("ix_performance_records_generated_asset_id", table_name="performance_records")
    op.drop_index("ix_performance_records_product_id", table_name="performance_records")
    op.drop_table("performance_records")
