"""Database access dedicated to Store records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.store import Store


class StoreRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, store: Store) -> Store:
        self.db.add(store)
        return store

    def get_by_id(self, store_id: int) -> Store | None:
        return self.db.get(Store, store_id)

    def list(self, *, offset: int, limit: int) -> tuple[list[Store], int]:
        items = list(
            self.db.scalars(
                select(Store).order_by(Store.id).offset(offset).limit(limit)
            )
        )
        total = self.db.scalar(select(func.count()).select_from(Store)) or 0
        return items, total

    def update(self, store: Store, changes: dict[str, Any]) -> Store:
        for field_name, value in changes.items():
            setattr(store, field_name, value)
        return store
