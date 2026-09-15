"""Inventory use cases and the inventory/movement transaction boundary."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.inventory import InventoryItem, InventoryMovement, InventoryMovementType
from app.models.product_sku import ProductSku, ProductSkuStatus
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_sku_repository import ProductSkuRepository
from app.schemas.inventory import InventoryAdjustment, InventorySettingsUpdate


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.skus = ProductSkuRepository(db)
        self.inventory = InventoryRepository(db)

    def get(self, sku_id: int) -> InventoryItem:
        self._require_sku(sku_id)
        return self._require_inventory(sku_id)

    def adjust(self, sku_id: int, payload: InventoryAdjustment) -> InventoryItem:
        sku = self._require_active_sku(sku_id)
        inventory = self._require_inventory(sku.id)
        before_qty = inventory.stock_qty
        after_qty = before_qty + payload.change_qty
        if after_qty < inventory.locked_qty:
            raise AppError(
                status_code=409,
                code="insufficient_stock",
                message="Stock cannot be lower than locked quantity",
            )

        movement_type = payload.movement_type
        if movement_type is None:
            movement_type = (
                InventoryMovementType.INBOUND
                if payload.change_qty > 0
                else InventoryMovementType.OUTBOUND
            )

        movement = InventoryMovement(
            sku_id=sku.id,
            movement_type=movement_type,
            change_qty=payload.change_qty,
            before_qty=before_qty,
            after_qty=after_qty,
            reason_text=payload.reason_text,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
        )

        try:
            self.inventory.update_item(inventory, {"stock_qty": after_qty})
            self.inventory.add_movement(movement)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(inventory)
        return inventory

    def update_settings(
        self, sku_id: int, payload: InventorySettingsUpdate
    ) -> InventoryItem:
        sku = self._require_active_sku(sku_id)
        inventory = self._require_inventory(sku.id)
        changes = payload.model_dump(exclude_unset=True)
        self.inventory.update_item(inventory, changes)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    def list_movements(
        self, *, sku_id: int, page: int, page_size: int
    ) -> tuple[list[InventoryMovement], int]:
        self._require_sku(sku_id)
        offset = (page - 1) * page_size
        return self.inventory.list_movements(
            sku_id=sku_id,
            offset=offset,
            limit=page_size,
        )

    def _require_sku(self, sku_id: int) -> ProductSku:
        sku = self.skus.get_by_id(sku_id)
        if sku is None:
            raise AppError(
                status_code=404,
                code="sku_not_found",
                message=f"SKU {sku_id} was not found",
            )
        return sku

    def _require_active_sku(self, sku_id: int) -> ProductSku:
        sku = self._require_sku(sku_id)
        if sku.status is not ProductSkuStatus.ACTIVE:
            raise AppError(
                status_code=409,
                code="sku_inactive",
                message="Inactive SKU inventory is read-only",
            )
        return sku

    def _require_inventory(self, sku_id: int) -> InventoryItem:
        inventory = self.inventory.get_by_sku_id(sku_id)
        if inventory is None:
            raise AppError(
                status_code=500,
                code="inventory_not_initialized",
                message="SKU inventory was not initialized",
            )
        return inventory
