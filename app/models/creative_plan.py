"""Unified editable plans for main-image directions and video scripts."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.performance_record import PerformanceRecord
    from app.models.generation_job import GenerationJob
    from app.models.generated_asset import GeneratedAsset
    from app.models.product import Product


class CreativePlanType(str, Enum):
    MAIN_IMAGE = "main_image"
    VIDEO_SCRIPT = "video_script"


class CreativePlanStatus(str, Enum):
    DRAFT = "draft"
    SELECTED = "selected"
    ARCHIVED = "archived"


class CreativePlan(Base):
    __tablename__ = "creative_plans"
    __table_args__ = (
        Index(
            "uq_creative_plans_selected_product_type",
            "product_id",
            "plan_type",
            unique=True,
            postgresql_where=text("status = 'selected'"),
            sqlite_where=text("status = 'selected'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    plan_type: Mapped[CreativePlanType] = mapped_column(
        SqlEnum(
            CreativePlanType,
            name="creative_plan_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CreativePlanStatus] = mapped_column(
        SqlEnum(
            CreativePlanStatus,
            name="creative_plan_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=CreativePlanStatus.DRAFT,
        server_default=text("'draft'"),
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(200))
    usage_json: Mapped[dict[str, int] | None] = mapped_column(JSON)
    input_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="creative_plans")
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="creative_plan",
        passive_deletes=True,
    )
    generated_assets: Mapped[list["GeneratedAsset"]] = relationship(
        back_populates="creative_plan",
        passive_deletes=True,
    )
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="creative_plan", passive_deletes=True
    )
