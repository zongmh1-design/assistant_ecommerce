"""Create media generation jobs and append-only job events.

Revision ID: 20260915_0008
Revises: 20260915_0007
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0008"
down_revision: str | Sequence[str] | None = "20260915_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("creative_plan_id", sa.Integer(), nullable=False),
        sa.Column(
            "job_kind",
            sa.Enum(
                "image",
                "video",
                name="generation_job_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "job_status",
            sa.Enum(
                "pending",
                "running",
                "succeeded",
                "failed",
                "cancelled",
                "timeout",
                name="generation_job_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=100), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            "attempts >= 0", name="ck_generation_jobs_attempts_nonnegative"
        ),
        sa.CheckConstraint(
            "max_attempts >= 1", name="ck_generation_jobs_max_attempts_positive"
        ),
        sa.CheckConstraint(
            "attempts <= max_attempts",
            name="ck_generation_jobs_attempts_within_max",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_generation_jobs_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["creative_plan_id"],
            ["creative_plans.id"],
            name="fk_generation_jobs_creative_plan_id_creative_plans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_jobs_product_id", "generation_jobs", ["product_id"]
    )
    op.create_index(
        "ix_generation_jobs_creative_plan_id",
        "generation_jobs",
        ["creative_plan_id"],
    )
    op.create_index(
        "ix_generation_jobs_product_kind_status",
        "generation_jobs",
        ["product_id", "job_kind", "job_status"],
    )
    op.create_index(
        "ix_generation_jobs_status_locked_at",
        "generation_jobs",
        ["job_status", "locked_at"],
    )

    op.create_table(
        "generation_job_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "created",
                "started",
                "succeeded",
                "failed",
                "retry_requested",
                "cancelled",
                "timeout",
                name="generation_job_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("event_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["generation_jobs.id"],
            name="fk_generation_job_events_job_id_generation_jobs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_job_events_job_id",
        "generation_job_events",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generation_job_events_job_id", table_name="generation_job_events"
    )
    op.drop_table("generation_job_events")
    op.drop_index("ix_generation_jobs_status_locked_at", table_name="generation_jobs")
    op.drop_index(
        "ix_generation_jobs_product_kind_status", table_name="generation_jobs"
    )
    op.drop_index(
        "ix_generation_jobs_creative_plan_id", table_name="generation_jobs"
    )
    op.drop_index("ix_generation_jobs_product_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
