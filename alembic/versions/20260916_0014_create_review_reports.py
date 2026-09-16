"""Create historical structured operating review reports.

Revision ID: 20260916_0014
Revises: 20260916_0013
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0014"
down_revision: str | Sequence[str] | None = "20260916_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("insights_json", sa.JSON(), nullable=False),
        sa.Column("problem_judgements_json", sa.JSON(), nullable=False),
        sa.Column("next_actions_json", sa.JSON(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("usage_json", sa.JSON(), nullable=True),
        sa.Column("input_context_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("period_end > period_start", name="ck_review_reports_period_order"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_reports_product_id", "review_reports", ["product_id"])
    op.create_index("ix_review_reports_period_start", "review_reports", ["period_start"])
    op.create_index("ix_review_reports_period_end", "review_reports", ["period_end"])
    op.create_index("ix_review_reports_created_at", "review_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_review_reports_created_at", table_name="review_reports")
    op.drop_index("ix_review_reports_period_end", table_name="review_reports")
    op.drop_index("ix_review_reports_period_start", table_name="review_reports")
    op.drop_index("ix_review_reports_product_id", table_name="review_reports")
    op.drop_table("review_reports")
