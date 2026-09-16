"""Product model for the Phase 2A store-owned product catalog."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.store import Platform, Store

if TYPE_CHECKING:
    from app.models.competitor import Competitor, PublicLinkParseTask
    from app.models.ad_recommendation import AdRecommendation
    from app.models.ad_experiment import AdExperiment
    from app.models.performance_record import PerformanceRecord
    from app.models.creative_plan import CreativePlan
    from app.models.generation_job import GenerationJob
    from app.models.generated_asset import GeneratedAsset
    from app.models.promotion_link import PromotionLink
    from app.models.product_diagnosis import ProductDiagnosis
    from app.models.product_sku import ProductSku
    from app.models.review_report import ReviewReport


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[Platform] = mapped_column(
        SqlEnum(
            Platform,
            name="product_platform_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    target_audience: Mapped[str | None] = mapped_column(Text)
    selling_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    product_url: Mapped[str | None] = mapped_column(String(2048))
    images_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        SqlEnum(
            ProductStatus,
            name="product_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ProductStatus.DRAFT,
        server_default=text("'draft'"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store: Mapped[Store] = relationship(back_populates="products")
    skus: Mapped[list["ProductSku"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    link_parse_tasks: Mapped[list["PublicLinkParseTask"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    diagnoses: Mapped[list["ProductDiagnosis"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    creative_plans: Mapped[list["CreativePlan"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    generated_assets: Mapped[list["GeneratedAsset"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    promotion_links: Mapped[list["PromotionLink"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    ad_recommendations: Mapped[list["AdRecommendation"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    ad_experiments: Mapped[list["AdExperiment"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="product", passive_deletes=True
    )
    review_reports: Mapped[list["ReviewReport"]] = relationship(
        back_populates="product", passive_deletes=True
    )
