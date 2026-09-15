"""Store business use cases and transaction boundaries."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.store import Store
from app.repositories.store_repository import StoreRepository
from app.schemas.store import StoreCreate, StoreUpdate


class StoreService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.stores = StoreRepository(db)

    def create(self, payload: StoreCreate) -> Store:
        store = Store(**payload.model_dump())
        self.stores.add(store)
        self.db.commit()
        self.db.refresh(store)
        return store

    def list(self, *, page: int, page_size: int) -> tuple[list[Store], int]:
        offset = (page - 1) * page_size
        return self.stores.list(offset=offset, limit=page_size)

    def get(self, store_id: int) -> Store:
        store = self.stores.get_by_id(store_id)
        if store is None:
            raise _store_not_found_error(store_id)
        return store

    def update(self, store_id: int, payload: StoreUpdate) -> Store:
        store = self.get(store_id)
        changes = payload.model_dump(exclude_unset=True)
        self.stores.update(store, changes)
        self.db.commit()
        self.db.refresh(store)
        return store


def _store_not_found_error(store_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="store_not_found",
        message=f"Store {store_id} was not found",
    )
