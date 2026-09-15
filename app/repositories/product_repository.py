"""Database access dedicated to Product records and simple filters."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus
from app.models.store import Platform


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, product: Product) -> Product:
        self.db.add(product)
        return product

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def list(
        self,
        *,
        offset: int,
        limit: int,
        store_id: int | None = None,
        platform: Platform | None = None,
        status: ProductStatus | None = None,
    ) -> tuple[list[Product], int]:
        filters = []
        if store_id is not None:
            filters.append(Product.store_id == store_id)
        if platform is not None:
            filters.append(Product.platform == platform)
        if status is not None:
            filters.append(Product.status == status)

        item_statement = select(Product).where(*filters).order_by(Product.id)
        count_statement = select(func.count()).select_from(Product).where(*filters)
        items = list(
            self.db.scalars(item_statement.offset(offset).limit(limit))
        )
        total = self.db.scalar(count_statement) or 0
        return items, total

    def update(self, product: Product, changes: dict[str, Any]) -> Product:
        for field_name, value in changes.items():
            setattr(product, field_name, value)
        return product
