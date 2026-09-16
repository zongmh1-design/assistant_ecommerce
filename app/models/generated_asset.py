"""Reviewed media assets promoted from validated successful generation jobs."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ad_experiment import AdExperiment
    from app.models.performance_record import PerformanceRecord
    from app.models.creative_plan import CreativePlan
    from app.models.generation_job import GenerationJob
    from app.models.product import Product


class GeneratedAssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class AssetReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"
    __table_args__ = (
        UniqueConstraint(
            "generation_job_id",
            name="uq_generated_assets_generation_job_id",
        ),
        UniqueConstraint(
            "product_id",
            "creative_plan_id",
            "asset_type",
            "version_no",
            name="uq_generated_assets_plan_type_version",
        ),
        CheckConstraint("version_no >= 1", name="ck_generated_assets_version_positive"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_generated_assets_score_range",
        ),
        CheckConstraint(
            "width IS NULL OR width > 0", name="ck_generated_assets_width_positive"
        ),
        CheckConstraint(
            "height IS NULL OR height > 0", name="ck_generated_assets_height_positive"
        ),
        CheckConstraint(
            "duration_sec IS NULL OR duration_sec > 0",
            name="ck_generated_assets_duration_positive",
        ),
        CheckConstraint(
            "asset_type != 'image' OR (width IS NOT NULL AND height IS NOT NULL)",
            name="ck_generated_assets_image_dimensions",
        ),
        CheckConstraint(
            "asset_type != 'video' OR duration_sec IS NOT NULL",
            name="ck_generated_assets_video_duration",
        ),
        Index(
            "ix_generated_assets_product_type_review",
            "product_id",
            "asset_type",
            "review_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    creative_plan_id: Mapped[int] = mapped_column(
        ForeignKey("creative_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    generation_job_id: Mapped[int] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset_type: Mapped[GeneratedAssetType] = mapped_column(
        SqlEnum(
            GeneratedAssetType,
            name="generated_asset_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    asset_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    review_status: Mapped[AssetReviewStatus] = mapped_column(
        SqlEnum(
            AssetReviewStatus,
            name="asset_review_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=AssetReviewStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_scene: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[int | None] = mapped_column(Integer)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="generated_assets")
    creative_plan: Mapped["CreativePlan"] = relationship(
        back_populates="generated_assets"
    )
    generation_job: Mapped["GenerationJob"] = relationship(
        back_populates="generated_asset"
    )
    ad_experiments: Mapped[list["AdExperiment"]] = relationship(
        back_populates="related_asset", passive_deletes=True
    )
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="generated_asset", passive_deletes=True
    )
