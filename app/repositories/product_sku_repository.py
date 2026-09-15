"""Database access dedicated to ProductSku records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product_sku import ProductSku


class ProductSkuRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, sku: ProductSku) -> ProductSku:
        self.db.add(sku)
        return sku

    def get_by_id(self, sku_id: int) -> ProductSku | None:
        return self.db.get(ProductSku, sku_id)

    def get_by_product_and_code(
        self, product_id: int, sku_code: str
    ) -> ProductSku | None:
        statement = select(ProductSku).where(
            ProductSku.product_id == product_id,
            ProductSku.sku_code == sku_code,
        )
        return self.db.scalar(statement)

    def list_by_product(
        self, *, product_id: int, offset: int, limit: int
    ) -> tuple[list[ProductSku], int]:
        condition = ProductSku.product_id == product_id
        items = list(
            self.db.scalars(
                select(ProductSku)
                .where(condition)
                .order_by(ProductSku.id)
                .offset(offset)
                .limit(limit)
            )
        )
        total = (
            self.db.scalar(
                select(func.count()).select_from(ProductSku).where(condition)
            )
            or 0
        )
        return items, total

    def update(self, sku: ProductSku, changes: dict[str, Any]) -> ProductSku:
        for field_name, value in changes.items():
            setattr(sku, field_name, value)
        return sku
