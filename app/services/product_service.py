"""Product business use cases, including mandatory Store validation."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.product import Product, ProductStatus
from app.models.store import Platform
from app.repositories.product_repository import ProductRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.stores = StoreRepository(db)

    def create(self, payload: ProductCreate) -> Product:
        self._require_store(payload.store_id)
        product = Product(**payload.model_dump())
        self.products.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def list(
        self,
        *,
        page: int,
        page_size: int,
        store_id: int | None = None,
        platform: Platform | None = None,
        status: ProductStatus | None = None,
        require_store: bool = False,
    ) -> tuple[list[Product], int]:
        if require_store and store_id is not None:
            self._require_store(store_id)
        offset = (page - 1) * page_size
        return self.products.list(
            offset=offset,
            limit=page_size,
            store_id=store_id,
            platform=platform,
            status=status,
        )

    def get(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def update(self, product_id: int, payload: ProductUpdate) -> Product:
        product = self.get(product_id)
        changes = payload.model_dump(exclude_unset=True)
        if "store_id" in changes:
            self._require_store(changes["store_id"])
        self.products.update(product, changes)
        self.db.commit()
        self.db.refresh(product)
        return product

    def _require_store(self, store_id: int) -> None:
        if self.stores.get_by_id(store_id) is None:
            raise AppError(
                status_code=404,
                code="store_not_found",
                message=f"Store {store_id} was not found",
            )
