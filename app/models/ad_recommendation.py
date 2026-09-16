"""Historical AI-assisted advertising recommendations with human decisions."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ad_experiment import AdExperiment
    from app.models.product import Product
    from app.models.user import User


class AdRecommendationConfirmStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class AdRecommendation(Base):
    __tablename__ = "ad_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    objective_text: Mapped[str] = mapped_column(Text, nullable=False)
    audience_segments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    budget_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    creative_tests_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    bid_strategy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    risk_controls_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    next_steps_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    confirm_status: Mapped[AdRecommendationConfirmStatus] = mapped_column(
        SqlEnum(
            AdRecommendationConfirmStatus,
            name="ad_recommendation_confirm_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=AdRecommendationConfirmStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
        index=True,
    )
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirm_remark: Mapped[str | None] = mapped_column(Text)
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

    product: Mapped["Product"] = relationship(back_populates="ad_recommendations")
    confirmer: Mapped["User | None"] = relationship(foreign_keys=[confirmed_by])
    ad_experiments: Mapped[list["AdExperiment"]] = relationship(
        back_populates="ad_recommendation", passive_deletes=True
    )
