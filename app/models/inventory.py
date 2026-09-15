"""Current SKU inventory and its immutable quantity-change history."""

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.product_sku import ProductSku


class InventoryMovementType(str, Enum):
    INITIAL = "initial"
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    ADJUSTMENT = "adjustment"


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("sku_id", name="uq_inventory_items_sku_id"),
        CheckConstraint("stock_qty >= 0", name="ck_inventory_items_stock_nonnegative"),
        CheckConstraint("locked_qty >= 0", name="ck_inventory_items_locked_nonnegative"),
        CheckConstraint(
            "warning_threshold >= 0",
            name="ck_inventory_items_warning_nonnegative",
        ),
        CheckConstraint(
            "locked_qty <= stock_qty",
            name="ck_inventory_items_locked_not_over_stock",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("product_skus.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location_text: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sku: Mapped[ProductSku] = relationship(back_populates="inventory")

    @property
    def available_qty(self) -> int:
        return self.stock_qty - self.locked_qty


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("before_qty >= 0", name="ck_inventory_movements_before_nonnegative"),
        CheckConstraint("after_qty >= 0", name="ck_inventory_movements_after_nonnegative"),
        CheckConstraint(
            "after_qty = before_qty + change_qty",
            name="ck_inventory_movements_quantity_equation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(
        ForeignKey("product_skus.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        SqlEnum(
            InventoryMovementType,
            name="inventory_movement_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
    )
    change_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    before_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    after_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sku: Mapped[ProductSku] = relationship(back_populates="movements")
