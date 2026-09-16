"""Create historical structured product diagnoses.

Revision ID: 20260915_0005
Revises: 20260915_0004
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0005"
down_revision: str | Sequence[str] | None = "20260915_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_diagnoses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("positioning", sa.Text(), nullable=False),
        sa.Column("price_band", sa.Text(), nullable=False),
        sa.Column("audience_insights", sa.JSON(), nullable=False),
        sa.Column("pain_points", sa.JSON(), nullable=False),
        sa.Column("selling_point_analysis", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("input_context_json", sa.JSON(), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=False),
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
            name="fk_product_diagnoses_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_diagnoses_product_id",
        "product_diagnoses",
        ["product_id"],
    )
    op.create_index(
        "ix_product_diagnoses_source_type",
        "product_diagnoses",
        ["source_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_diagnoses_source_type", table_name="product_diagnoses")
    op.drop_index("ix_product_diagnoses_product_id", table_name="product_diagnoses")
    op.drop_table("product_diagnoses")
