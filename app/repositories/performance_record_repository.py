"""Database access dedicated to manually entered performance records."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.performance_record import PerformanceRecord


class PerformanceRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, record: PerformanceRecord) -> PerformanceRecord:
        self.db.add(record)
        return record

    def get_by_id_and_product_id(
        self, record_id: int, product_id: int
    ) -> PerformanceRecord | None:
        return self.db.scalar(
            select(PerformanceRecord).where(
                PerformanceRecord.id == record_id,
                PerformanceRecord.product_id == product_id,
            )
        )

    def get_for_update_by_id_and_product_id(
        self, record_id: int, product_id: int
    ) -> PerformanceRecord | None:
        return self.db.scalar(
            select(PerformanceRecord)
            .where(
                PerformanceRecord.id == record_id,
                PerformanceRecord.product_id == product_id,
            )
            .with_for_update()
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        experiment_id: int | None,
        generated_asset_id: int | None,
        promotion_link_id: int | None,
        period_start_from: datetime | None,
        period_end_to: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[PerformanceRecord], int]:
        conditions = [PerformanceRecord.product_id == product_id]
        if experiment_id is not None:
            conditions.append(PerformanceRecord.experiment_id == experiment_id)
        if generated_asset_id is not None:
            conditions.append(
                PerformanceRecord.generated_asset_id == generated_asset_id
            )
        if promotion_link_id is not None:
            conditions.append(
                PerformanceRecord.promotion_link_id == promotion_link_id
            )
        if period_start_from is not None:
            conditions.append(PerformanceRecord.period_start >= period_start_from)
        if period_end_to is not None:
            conditions.append(PerformanceRecord.period_end <= period_end_to)

        items = list(
            self.db.scalars(
                select(PerformanceRecord)
                .where(*conditions)
                .order_by(
                    PerformanceRecord.period_start.desc(),
                    PerformanceRecord.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(PerformanceRecord).where(*conditions)
        ) or 0
        return items, total

    def update(
        self, record: PerformanceRecord, changes: dict[str, Any]
    ) -> PerformanceRecord:
        for field_name, value in changes.items():
            setattr(record, field_name, value)
        return record
