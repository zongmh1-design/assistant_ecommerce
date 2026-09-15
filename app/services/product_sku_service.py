"""SKU use cases, including atomic inventory initialization."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.inventory import InventoryItem, InventoryMovement, InventoryMovementType
from app.models.product_sku import ProductSku
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_sku_repository import ProductSkuRepository
from app.schemas.product_sku import ProductSkuCreate, ProductSkuUpdate


class ProductSkuService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.skus = ProductSkuRepository(db)
        self.inventory = InventoryRepository(db)

    def create(self, product_id: int, payload: ProductSkuCreate) -> ProductSku:
        self._require_product(product_id)
        if self.skus.get_by_product_and_code(product_id, payload.sku_code) is not None:
            raise _sku_code_conflict(payload.sku_code)

        sku = ProductSku(product_id=product_id, **payload.model_dump())
        self.skus.add(sku)
        try:
            self.db.flush()
            self.inventory.add_item(
                InventoryItem(
                    sku_id=sku.id,
                    stock_qty=0,
                    locked_qty=0,
                    warning_threshold=0,
                )
            )
            self.inventory.add_movement(
                InventoryMovement(
                    sku_id=sku.id,
                    movement_type=InventoryMovementType.INITIAL,
                    change_qty=0,
                    before_qty=0,
                    after_qty=0,
                    reason_text="SKU inventory initialized",
                )
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise _sku_code_conflict(payload.sku_code) from exc

        self.db.refresh(sku)
        return sku

    def list(
        self, *, product_id: int, page: int, page_size: int
    ) -> tuple[list[ProductSku], int]:
        self._require_product(product_id)
        offset = (page - 1) * page_size
        return self.skus.list_by_product(
            product_id=product_id,
            offset=offset,
            limit=page_size,
        )

    def get(self, sku_id: int) -> ProductSku:
        sku = self.skus.get_by_id(sku_id)
        if sku is None:
            raise _sku_not_found_error(sku_id)
        return sku

    def update(self, sku_id: int, payload: ProductSkuUpdate) -> ProductSku:
        sku = self.get(sku_id)
        changes = payload.model_dump(exclude_unset=True)
        new_code = changes.get("sku_code")
        if new_code is not None and new_code != sku.sku_code:
            existing = self.skus.get_by_product_and_code(sku.product_id, new_code)
            if existing is not None:
                raise _sku_code_conflict(new_code)
        self.skus.update(sku, changes)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise _sku_code_conflict(changes.get("sku_code", sku.sku_code)) from exc
        self.db.refresh(sku)
        return sku

    def _require_product(self, product_id: int) -> None:
        if self.products.get_by_id(product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )


def _sku_not_found_error(sku_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="sku_not_found",
        message=f"SKU {sku_id} was not found",
    )


def _sku_code_conflict(sku_code: str) -> AppError:
    return AppError(
        status_code=409,
        code="sku_code_conflict",
        message=f"SKU code '{sku_code}' already exists for this product",
    )
