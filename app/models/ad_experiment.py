"""Human-controlled experiment plans; no advertising execution capability."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ad_recommendation import AdRecommendation
    from app.models.generated_asset import GeneratedAsset
    from app.models.product import Product
    from app.models.promotion_link import PromotionLink
    from app.models.performance_record import PerformanceRecord


class AdExperimentStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class AdExperiment(Base):
    __tablename__ = "ad_experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ad_recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("ad_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    related_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_assets.id", ondelete="RESTRICT"), nullable=True
    )
    related_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("promotion_links.id", ondelete="RESTRICT"), nullable=True
    )
    experiment_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    audience_text: Mapped[str] = mapped_column(Text, nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    success_metric_text: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    experiment_status: Mapped[AdExperimentStatus] = mapped_column(
        SqlEnum(
            AdExperimentStatus,
            name="ad_experiment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=AdExperimentStatus.DRAFT,
        server_default=text("'draft'"),
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(200))
    usage_json: Mapped[dict[str, int] | None] = mapped_column(JSON)
    input_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="ad_experiments")
    ad_recommendation: Mapped["AdRecommendation"] = relationship(back_populates="ad_experiments")
    related_asset: Mapped["GeneratedAsset | None"] = relationship(back_populates="ad_experiments")
    related_link: Mapped["PromotionLink | None"] = relationship(back_populates="ad_experiments")
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="experiment", passive_deletes=True
    )
