"""Product SKU model with product-scoped SKU code uniqueness."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.product import Product

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem, InventoryMovement


class ProductSkuStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProductSku(Base):
    __tablename__ = "product_skus"
    __table_args__ = (
        UniqueConstraint("product_id", "sku_code", name="uq_product_skus_product_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sku_code: Mapped[str] = mapped_column(String(100), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False)
    spec_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[ProductSkuStatus] = mapped_column(
        SqlEnum(
            ProductSkuStatus,
            name="product_sku_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ProductSkuStatus.ACTIVE,
        server_default=text("'active'"),
        nullable=False,
        index=True,
    )
    platform_sku_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped[Product] = relationship(back_populates="skus")
    inventory: Mapped["InventoryItem"] = relationship(
        back_populates="sku",
        uselist=False,
        passive_deletes=True,
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="sku",
        passive_deletes=True,
    )
