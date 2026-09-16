"""Product promotion links and their minimal click audit records."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ad_experiment import AdExperiment
    from app.models.performance_record import PerformanceRecord
    from app.models.product import Product


class PromotionLinkStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PromotionLink(Base):
    __tablename__ = "promotion_links"
    __table_args__ = (
        CheckConstraint(
            "click_count >= 0", name="ck_promotion_links_click_count_nonnegative"
        ),
        Index("uq_promotion_links_tracking_code", "tracking_code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    link_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    tracking_code: Mapped[str] = mapped_column(String(64), nullable=False)
    utm_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[PromotionLinkStatus] = mapped_column(
        SqlEnum(
            PromotionLinkStatus,
            name="promotion_link_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=PromotionLinkStatus.ACTIVE,
        server_default=text("'active'"),
        nullable=False,
        index=True,
    )
    click_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    scene_text: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="promotion_links")
    clicks: Mapped[list["PromotionLinkClick"]] = relationship(
        back_populates="promotion_link",
        passive_deletes=True,
        order_by="PromotionLinkClick.id",
    )
    ad_experiments: Mapped[list["AdExperiment"]] = relationship(
        back_populates="related_link", passive_deletes=True
    )
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="promotion_link", passive_deletes=True
    )


class PromotionLinkClick(Base):
    __tablename__ = "promotion_link_clicks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promotion_link_id: Mapped[int] = mapped_column(
        ForeignKey("promotion_links.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    promotion_link: Mapped[PromotionLink] = relationship(back_populates="clicks")
