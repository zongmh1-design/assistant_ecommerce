"""Database access dedicated to CreativePlan records."""

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType


class CreativePlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, plan: CreativePlan) -> CreativePlan:
        self.db.add(plan)
        return plan

    def get_by_id_and_product_id(
        self, plan_id: int, product_id: int
    ) -> CreativePlan | None:
        statement = select(CreativePlan).where(
            CreativePlan.id == plan_id,
            CreativePlan.product_id == product_id,
        )
        return self.db.scalar(statement)

    def get_for_update_by_id_and_product_id(
        self, plan_id: int, product_id: int
    ) -> CreativePlan | None:
        statement = (
            select(CreativePlan)
            .where(
                CreativePlan.id == plan_id,
                CreativePlan.product_id == product_id,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def get_latest_selected_by_product(self, product_id: int) -> CreativePlan | None:
        return self.db.scalar(
            select(CreativePlan)
            .where(
                CreativePlan.product_id == product_id,
                CreativePlan.status == CreativePlanStatus.SELECTED,
            )
            .order_by(CreativePlan.created_at.desc(), CreativePlan.id.desc())
            .limit(1)
        )

    def list_selected_for_ad_context(self, product_id: int) -> list[CreativePlan]:
        return list(
            self.db.scalars(
                select(CreativePlan)
                .where(
                    CreativePlan.product_id == product_id,
                    CreativePlan.status == CreativePlanStatus.SELECTED,
                )
                .order_by(CreativePlan.plan_type, CreativePlan.id)
            )
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        plan_type: CreativePlanType | None,
        status: CreativePlanStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[CreativePlan], int]:
        conditions = [CreativePlan.product_id == product_id]
        if plan_type is not None:
            conditions.append(CreativePlan.plan_type == plan_type)
        if status is not None:
            conditions.append(CreativePlan.status == status)
        items = list(
            self.db.scalars(
                select(CreativePlan)
                .where(*conditions)
                .order_by(CreativePlan.created_at.desc(), CreativePlan.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = (
            self.db.scalar(
                select(func.count()).select_from(CreativePlan).where(*conditions)
            )
            or 0
        )
        return items, total

    def archive_selected(
        self,
        *,
        product_id: int,
        plan_type: CreativePlanType,
        exclude_plan_id: int,
    ) -> None:
        self.db.execute(
            update(CreativePlan)
            .where(
                CreativePlan.product_id == product_id,
                CreativePlan.plan_type == plan_type,
                CreativePlan.status == CreativePlanStatus.SELECTED,
                CreativePlan.id != exclude_plan_id,
            )
            .values(status=CreativePlanStatus.ARCHIVED)
        )

    def update(self, plan: CreativePlan, changes: dict[str, Any]) -> CreativePlan:
        for field_name, value in changes.items():
            setattr(plan, field_name, value)
        return plan
