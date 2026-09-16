"""Append and query GenerationJobEvent records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generation_job import GenerationJobEvent


class GenerationJobEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, event: GenerationJobEvent) -> GenerationJobEvent:
        self.db.add(event)
        return event

    def list_by_job(self, job_id: int) -> list[GenerationJobEvent]:
        return list(
            self.db.scalars(
                select(GenerationJobEvent)
                .where(GenerationJobEvent.job_id == job_id)
                .order_by(GenerationJobEvent.id)
            )
        )
