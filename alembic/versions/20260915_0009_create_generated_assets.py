"""Create reviewed assets synchronized from successful generation jobs.

Revision ID: 20260915_0009
Revises: 20260915_0008
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0009"
down_revision: str | Sequence[str] | None = "20260915_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("creative_plan_id", sa.Integer(), nullable=False),
        sa.Column("generation_job_id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "image",
                "video",
                name="generated_asset_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("asset_url", sa.String(length=2048), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column(
            "review_status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="asset_review_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("usage_scene", sa.String(length=200), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint(
            "version_no >= 1", name="ck_generated_assets_version_positive"
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_generated_assets_score_range",
        ),
        sa.CheckConstraint(
            "width IS NULL OR width > 0",
            name="ck_generated_assets_width_positive",
        ),
        sa.CheckConstraint(
            "height IS NULL OR height > 0",
            name="ck_generated_assets_height_positive",
        ),
        sa.CheckConstraint(
            "duration_sec IS NULL OR duration_sec > 0",
            name="ck_generated_assets_duration_positive",
        ),
        sa.CheckConstraint(
            "asset_type != 'image' OR (width IS NOT NULL AND height IS NOT NULL)",
            name="ck_generated_assets_image_dimensions",
        ),
        sa.CheckConstraint(
            "asset_type != 'video' OR duration_sec IS NOT NULL",
            name="ck_generated_assets_video_duration",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_generated_assets_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["creative_plan_id"],
            ["creative_plans.id"],
            name="fk_generated_assets_creative_plan_id_creative_plans",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generation_job_id"],
            ["generation_jobs.id"],
            name="fk_generated_assets_generation_job_id_generation_jobs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_job_id",
            name="uq_generated_assets_generation_job_id",
        ),
        sa.UniqueConstraint(
            "product_id",
            "creative_plan_id",
            "asset_type",
            "version_no",
            name="uq_generated_assets_plan_type_version",
        ),
    )
    op.create_index(
        "ix_generated_assets_product_id", "generated_assets", ["product_id"]
    )
    op.create_index(
        "ix_generated_assets_creative_plan_id",
        "generated_assets",
        ["creative_plan_id"],
    )
    op.create_index(
        "ix_generated_assets_product_type_review",
        "generated_assets",
        ["product_id", "asset_type", "review_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_assets_product_type_review", table_name="generated_assets"
    )
    op.drop_index(
        "ix_generated_assets_creative_plan_id", table_name="generated_assets"
    )
    op.drop_index("ix_generated_assets_product_id", table_name="generated_assets")
    op.drop_table("generated_assets")
