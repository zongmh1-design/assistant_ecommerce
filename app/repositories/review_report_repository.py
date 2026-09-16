"""Database access for historical review reports and their source records."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, not_, select
from sqlalchemy.orm import Session, selectinload

from app.models.performance_record import PerformanceRecord
from app.models.review_report import ReviewReport


class ReviewReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, report: ReviewReport) -> ReviewReport:
        self.db.add(report)
        return report

    def get_by_id_and_product_id(self, report_id: int, product_id: int) -> ReviewReport | None:
        return self.db.scalar(
            select(ReviewReport).where(
                ReviewReport.id == report_id,
                ReviewReport.product_id == product_id,
            )
        )

    def list_by_product(
        self, *, product_id: int, period_start_from: datetime | None,
        period_end_to: datetime | None, offset: int, limit: int,
    ) -> tuple[list[ReviewReport], int]:
        conditions = [ReviewReport.product_id == product_id]
        if period_start_from is not None:
            conditions.append(ReviewReport.period_start >= period_start_from)
        if period_end_to is not None:
            conditions.append(ReviewReport.period_end <= period_end_to)
        items = list(self.db.scalars(
            select(ReviewReport).where(*conditions)
            .order_by(ReviewReport.created_at.desc(), ReviewReport.id.desc())
            .offset(offset).limit(limit)
        ))
        total = self.db.scalar(
            select(func.count()).select_from(ReviewReport).where(*conditions)
        ) or 0
        return items, total

    def list_source_records(
        self, product_id: int, period_start: datetime, period_end: datetime
    ) -> list[PerformanceRecord]:
        return list(self.db.scalars(
            select(PerformanceRecord)
            .where(
                PerformanceRecord.product_id == product_id,
                PerformanceRecord.period_start >= period_start,
                PerformanceRecord.period_end <= period_end,
            )
            .options(
                selectinload(PerformanceRecord.experiment),
                selectinload(PerformanceRecord.generated_asset),
                selectinload(PerformanceRecord.promotion_link),
            )
            .order_by(PerformanceRecord.period_start, PerformanceRecord.id)
        ))

    def count_excluded_overlapping_records(
        self, product_id: int, period_start: datetime, period_end: datetime
    ) -> int:
        fully_contained = (
            (PerformanceRecord.period_start >= period_start)
            & (PerformanceRecord.period_end <= period_end)
        )
        return self.db.scalar(
            select(func.count()).select_from(PerformanceRecord).where(
                PerformanceRecord.product_id == product_id,
                PerformanceRecord.period_start < period_end,
                PerformanceRecord.period_end > period_start,
                not_(fully_contained),
            )
        ) or 0

    def update(self, report: ReviewReport, changes: dict[str, Any]) -> ReviewReport:
        for field_name, value in changes.items():
            setattr(report, field_name, value)
        return report
