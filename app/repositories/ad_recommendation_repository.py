"""Database access dedicated to historical AdRecommendation records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus


class AdRecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, recommendation: AdRecommendation) -> AdRecommendation:
        self.db.add(recommendation)
        return recommendation

    def get_by_id_and_product_id(
        self, recommendation_id: int, product_id: int
    ) -> AdRecommendation | None:
        return self.db.scalar(
            select(AdRecommendation).where(
                AdRecommendation.id == recommendation_id,
                AdRecommendation.product_id == product_id,
            )
        )

    def get_for_update_by_id_and_product_id(
        self, recommendation_id: int, product_id: int
    ) -> AdRecommendation | None:
        return self.db.scalar(
            select(AdRecommendation)
            .where(
                AdRecommendation.id == recommendation_id,
                AdRecommendation.product_id == product_id,
            )
            .with_for_update()
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        confirm_status: AdRecommendationConfirmStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AdRecommendation], int]:
        conditions = [AdRecommendation.product_id == product_id]
        if confirm_status is not None:
            conditions.append(AdRecommendation.confirm_status == confirm_status)
        items = list(
            self.db.scalars(
                select(AdRecommendation)
                .where(*conditions)
                .order_by(AdRecommendation.created_at.desc(), AdRecommendation.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(AdRecommendation).where(*conditions)
        ) or 0
        return items, total

    def get_latest_confirmed_for_product(
        self, product_id: int
    ) -> AdRecommendation | None:
        return self.db.scalar(
            select(AdRecommendation)
            .where(
                AdRecommendation.product_id == product_id,
                AdRecommendation.confirm_status == AdRecommendationConfirmStatus.CONFIRMED,
            )
            .order_by(AdRecommendation.created_at.desc(), AdRecommendation.id.desc())
            .limit(1)
        )

    def update(
        self, recommendation: AdRecommendation, changes: dict[str, Any]
    ) -> AdRecommendation:
        for field_name, value in changes.items():
            setattr(recommendation, field_name, value)
        return recommendation
