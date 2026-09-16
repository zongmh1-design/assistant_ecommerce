"""Create promotion links and basic click audit records.

Revision ID: 20260915_0010
Revises: 20260915_0009
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0010"
down_revision: str | Sequence[str] | None = "20260915_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promotion_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("link_name", sa.String(length=200), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("tracking_code", sa.String(length=64), nullable=False),
        sa.Column("utm_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active", "inactive", name="promotion_link_status",
                native_enum=False, create_constraint=True,
            ),
            server_default=sa.text("'active'"), nullable=False,
        ),
        sa.Column("click_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("scene_text", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("click_count >= 0", name="ck_promotion_links_click_count_nonnegative"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_promotion_links_product_id_products", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_promotion_links_tracking_code", "promotion_links", ["tracking_code"], unique=True)
    op.create_index("ix_promotion_links_product_id", "promotion_links", ["product_id"])
    op.create_index("ix_promotion_links_status", "promotion_links", ["status"])

    op.create_table(
        "promotion_link_clicks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("promotion_link_id", sa.Integer(), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["promotion_link_id"], ["promotion_links.id"],
            name="fk_promotion_link_clicks_link_id_promotion_links", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promotion_link_clicks_promotion_link_id", "promotion_link_clicks", ["promotion_link_id"])
    op.create_index("ix_promotion_link_clicks_clicked_at", "promotion_link_clicks", ["clicked_at"])


def downgrade() -> None:
    op.drop_index("ix_promotion_link_clicks_clicked_at", table_name="promotion_link_clicks")
    op.drop_index("ix_promotion_link_clicks_promotion_link_id", table_name="promotion_link_clicks")
    op.drop_table("promotion_link_clicks")
    op.drop_index("ix_promotion_links_status", table_name="promotion_links")
    op.drop_index("ix_promotion_links_product_id", table_name="promotion_links")
    op.drop_index("uq_promotion_links_tracking_code", table_name="promotion_links")
    op.drop_table("promotion_links")
