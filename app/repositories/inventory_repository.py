"""Database access for current inventory and inventory movement history."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, InventoryMovement


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_item(self, inventory: InventoryItem) -> InventoryItem:
        self.db.add(inventory)
        return inventory

    def get_by_sku_id(self, sku_id: int) -> InventoryItem | None:
        statement = select(InventoryItem).where(InventoryItem.sku_id == sku_id)
        return self.db.scalar(statement)

    def update_item(
        self, inventory: InventoryItem, changes: dict[str, Any]
    ) -> InventoryItem:
        for field_name, value in changes.items():
            setattr(inventory, field_name, value)
        return inventory

    def add_movement(self, movement: InventoryMovement) -> InventoryMovement:
        self.db.add(movement)
        return movement

    def list_movements(
        self, *, sku_id: int, offset: int, limit: int
    ) -> tuple[list[InventoryMovement], int]:
        condition = InventoryMovement.sku_id == sku_id
        items = list(
            self.db.scalars(
                select(InventoryMovement)
                .where(condition)
                .order_by(InventoryMovement.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = (
            self.db.scalar(
                select(func.count()).select_from(InventoryMovement).where(condition)
            )
            or 0
        )
        return items, total
