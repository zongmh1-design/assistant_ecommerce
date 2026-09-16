"""Database access dedicated to Competitor records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.competitor import Competitor


class CompetitorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, competitor: Competitor) -> Competitor:
        self.db.add(competitor)
        return competitor

    def get_by_id(self, competitor_id: int) -> Competitor | None:
        return self.db.get(Competitor, competitor_id)

    def list_by_product(
        self, *, product_id: int, offset: int, limit: int
    ) -> tuple[list[Competitor], int]:
        condition = Competitor.product_id == product_id
        items = list(
            self.db.scalars(
                select(Competitor)
                .where(condition)
                .order_by(Competitor.id)
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(select(func.count()).select_from(Competitor).where(condition)) or 0
        return items, total

    def list_for_diagnosis(self, product_id: int) -> list[Competitor]:
        statement = (
            select(Competitor)
            .where(Competitor.product_id == product_id)
            .order_by(Competitor.id)
        )
        return list(self.db.scalars(statement))

    def update(self, competitor: Competitor, changes: dict[str, Any]) -> Competitor:
        for field_name, value in changes.items():
            setattr(competitor, field_name, value)
        return competitor
