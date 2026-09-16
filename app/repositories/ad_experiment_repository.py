"""Database access dedicated to AdExperiment plans and status records."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ad_experiment import AdExperiment, AdExperimentStatus


class AdExperimentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, experiment: AdExperiment) -> AdExperiment:
        self.db.add(experiment)
        return experiment

    def get_by_id_and_product_id(
        self, experiment_id: int, product_id: int
    ) -> AdExperiment | None:
        return self.db.scalar(
            select(AdExperiment).where(
                AdExperiment.id == experiment_id,
                AdExperiment.product_id == product_id,
            )
        )

    def get_for_update_by_id_and_product_id(
        self, experiment_id: int, product_id: int
    ) -> AdExperiment | None:
        return self.db.scalar(
            select(AdExperiment)
            .where(
                AdExperiment.id == experiment_id,
                AdExperiment.product_id == product_id,
            )
            .with_for_update()
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        experiment_status: AdExperimentStatus | None,
        ad_recommendation_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AdExperiment], int]:
        conditions = [AdExperiment.product_id == product_id]
        if experiment_status is not None:
            conditions.append(AdExperiment.experiment_status == experiment_status)
        if ad_recommendation_id is not None:
            conditions.append(
                AdExperiment.ad_recommendation_id == ad_recommendation_id
            )
        items = list(
            self.db.scalars(
                select(AdExperiment)
                .where(*conditions)
                .order_by(AdExperiment.created_at.desc(), AdExperiment.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(AdExperiment).where(*conditions)
        ) or 0
        return items, total

    def update(
        self, experiment: AdExperiment, changes: dict[str, Any]
    ) -> AdExperiment:
        for field_name, value in changes.items():
            setattr(experiment, field_name, value)
        return experiment
