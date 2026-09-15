"""Inventory adjustment, settings, current-state and movement schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory import InventoryMovementType


class InventoryAdjustment(BaseModel):
    change_qty: int
    reason_text: str = Field(min_length=1, max_length=500)
    movement_type: InventoryMovementType | None = None
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_adjustment(self) -> "InventoryAdjustment":
        if self.change_qty == 0:
            raise ValueError("change_qty cannot be zero")
        if self.movement_type is InventoryMovementType.INITIAL:
            raise ValueError("initial movement can only be created with a SKU")
        if self.movement_type is InventoryMovementType.INBOUND and self.change_qty < 0:
            raise ValueError("inbound change_qty must be positive")
        if self.movement_type is InventoryMovementType.OUTBOUND and self.change_qty > 0:
            raise ValueError("outbound change_qty must be negative")
        return self


class InventorySettingsUpdate(BaseModel):
    warning_threshold: int | None = Field(default=None, ge=0)
    location_text: str | None = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_settings(self) -> "InventorySettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one setting must be provided")
        if (
            "warning_threshold" in self.model_fields_set
            and self.warning_threshold is None
        ):
            raise ValueError("warning_threshold cannot be null")
        return self


class InventoryRead(BaseModel):
    id: int
    sku_id: int
    stock_qty: int
    locked_qty: int
    warning_threshold: int
    location_text: str | None
    updated_at: datetime
    available_qty: int

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementRead(BaseModel):
    id: int
    sku_id: int
    movement_type: InventoryMovementType
    change_qty: int
    before_qty: int
    after_qty: int
    reason_text: str
    reference_type: str | None
    reference_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementListResponse(BaseModel):
    items: list[InventoryMovementRead]
    total: int
    page: int
    page_size: int
