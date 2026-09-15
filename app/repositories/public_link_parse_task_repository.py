"""Database access dedicated to public-link parsing tasks."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competitor import PublicLinkParseTask


class PublicLinkParseTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, task: PublicLinkParseTask) -> PublicLinkParseTask:
        self.db.add(task)
        return task

    def get_by_id_and_product_id(
        self, task_id: int, product_id: int
    ) -> PublicLinkParseTask | None:
        statement = select(PublicLinkParseTask).where(
            PublicLinkParseTask.id == task_id,
            PublicLinkParseTask.product_id == product_id,
        )
        return self.db.scalar(statement)

    def get_for_confirmation(
        self, task_id: int, product_id: int
    ) -> PublicLinkParseTask | None:
        statement = (
            select(PublicLinkParseTask)
            .where(
                PublicLinkParseTask.id == task_id,
                PublicLinkParseTask.product_id == product_id,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def update(
        self, task: PublicLinkParseTask, changes: dict[str, Any]
    ) -> PublicLinkParseTask:
        for field_name, value in changes.items():
            setattr(task, field_name, value)
        return task
