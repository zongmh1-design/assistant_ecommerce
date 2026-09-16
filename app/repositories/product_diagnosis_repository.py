"""Database access dedicated to historical ProductDiagnosis records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product_diagnosis import ProductDiagnosis


class ProductDiagnosisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, diagnosis: ProductDiagnosis) -> ProductDiagnosis:
        self.db.add(diagnosis)
        return diagnosis

    def get_by_id_and_product_id(
        self, diagnosis_id: int, product_id: int
    ) -> ProductDiagnosis | None:
        statement = select(ProductDiagnosis).where(
            ProductDiagnosis.id == diagnosis_id,
            ProductDiagnosis.product_id == product_id,
        )
        return self.db.scalar(statement)

    def list_by_product(
        self, *, product_id: int, offset: int, limit: int
    ) -> tuple[list[ProductDiagnosis], int]:
        condition = ProductDiagnosis.product_id == product_id
        items = list(
            self.db.scalars(
                select(ProductDiagnosis)
                .where(condition)
                .order_by(ProductDiagnosis.created_at.desc(), ProductDiagnosis.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = (
            self.db.scalar(
                select(func.count()).select_from(ProductDiagnosis).where(condition)
            )
            or 0
        )
        return items, total

    def get_latest_by_product(self, product_id: int) -> ProductDiagnosis | None:
        statement = (
            select(ProductDiagnosis)
            .where(ProductDiagnosis.product_id == product_id)
            .order_by(ProductDiagnosis.created_at.desc(), ProductDiagnosis.id.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def update(
        self, diagnosis: ProductDiagnosis, changes: dict[str, Any]
    ) -> ProductDiagnosis:
        for field_name, value in changes.items():
            setattr(diagnosis, field_name, value)
        return diagnosis
