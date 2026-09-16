"""Manually entered period performance with application-derived metrics."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ad_experiment import AdExperiment
    from app.models.creative_plan import CreativePlan
    from app.models.generated_asset import GeneratedAsset
    from app.models.product import Product
    from app.models.promotion_link import PromotionLink


class PerformanceRecord(Base):
    __tablename__ = "performance_records"
    __table_args__ = (
        CheckConstraint("period_end > period_start", name="ck_performance_records_period_order"),
        CheckConstraint("impressions >= 0", name="ck_performance_records_impressions_nonnegative"),
        CheckConstraint("clicks >= 0", name="ck_performance_records_clicks_nonnegative"),
        CheckConstraint("conversions >= 0", name="ck_performance_records_conversions_nonnegative"),
        CheckConstraint("clicks <= impressions", name="ck_performance_records_clicks_within_impressions"),
        CheckConstraint("conversions <= clicks", name="ck_performance_records_conversions_within_clicks"),
        CheckConstraint("spend >= 0", name="ck_performance_records_spend_nonnegative"),
        CheckConstraint("revenue >= 0", name="ck_performance_records_revenue_nonnegative"),
        CheckConstraint("ctr >= 0 AND ctr <= 1", name="ck_performance_records_ctr_range"),
        CheckConstraint(
            "conversion_rate >= 0 AND conversion_rate <= 1",
            name="ck_performance_records_conversion_rate_range",
        ),
        CheckConstraint(
            "(spend = 0 AND roi IS NULL) OR (spend > 0 AND roi IS NOT NULL)",
            name="ck_performance_records_roi_defined_by_spend",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    creative_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("creative_plans.id", ondelete="RESTRICT"), nullable=True
    )
    generated_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_assets.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    promotion_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("promotion_links.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    experiment_id: Mapped[int | None] = mapped_column(
        ForeignKey("ad_experiments.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    ctr: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    spend: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    roi: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="performance_records")
    creative_plan: Mapped["CreativePlan | None"] = relationship(back_populates="performance_records")
    generated_asset: Mapped["GeneratedAsset | None"] = relationship(back_populates="performance_records")
    promotion_link: Mapped["PromotionLink | None"] = relationship(back_populates="performance_records")
    experiment: Mapped["AdExperiment | None"] = relationship(back_populates="performance_records")
