"""Add provider, model and optional usage metadata to product diagnoses.

Revision ID: 20260915_0006
Revises: 20260915_0005
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0006"
down_revision: str | Sequence[str] | None = "20260915_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_diagnoses", sa.Column("provider_name", sa.String(100)))
    op.add_column("product_diagnoses", sa.Column("model_name", sa.String(200)))
    op.add_column("product_diagnoses", sa.Column("usage_json", sa.JSON()))


def downgrade() -> None:
    op.drop_column("product_diagnoses", "usage_json")
    op.drop_column("product_diagnoses", "model_name")
    op.drop_column("product_diagnoses", "provider_name")
