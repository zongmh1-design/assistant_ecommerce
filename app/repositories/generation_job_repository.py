"""Database access dedicated to GenerationJob records."""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus


class GenerationJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, job: GenerationJob) -> GenerationJob:
        self.db.add(job)
        return job

    def get_by_id_and_product_id(
        self, job_id: int, product_id: int
    ) -> GenerationJob | None:
        return self.db.scalar(
            select(GenerationJob).where(
                GenerationJob.id == job_id,
                GenerationJob.product_id == product_id,
            )
        )

    def get_for_update(
        self, job_id: int, product_id: int
    ) -> GenerationJob | None:
        return self.db.scalar(
            select(GenerationJob)
            .where(
                GenerationJob.id == job_id,
                GenerationJob.product_id == product_id,
            )
            .with_for_update()
        )

    def list_succeeded_ids_by_product(self, product_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(GenerationJob.id)
                .where(
                    GenerationJob.product_id == product_id,
                    GenerationJob.job_status == GenerationJobStatus.SUCCEEDED,
                )
                .order_by(GenerationJob.id)
            )
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        job_kind: GenerationJobKind | None,
        job_status: GenerationJobStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[GenerationJob], int]:
        conditions = [GenerationJob.product_id == product_id]
        if job_kind is not None:
            conditions.append(GenerationJob.job_kind == job_kind)
        if job_status is not None:
            conditions.append(GenerationJob.job_status == job_status)
        items = list(
            self.db.scalars(
                select(GenerationJob)
                .where(*conditions)
                .order_by(GenerationJob.created_at.desc(), GenerationJob.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(GenerationJob).where(*conditions)
        ) or 0
        return items, total

    def list_timed_out_for_update(self, cutoff: datetime) -> list[GenerationJob]:
        statement = (
            select(GenerationJob)
            .where(
                GenerationJob.job_status == GenerationJobStatus.RUNNING,
                or_(
                    GenerationJob.locked_at <= cutoff,
                    (
                        GenerationJob.locked_at.is_(None)
                        & (GenerationJob.started_at <= cutoff)
                    ),
                ),
            )
            .order_by(GenerationJob.id)
            .with_for_update()
        )
        return list(self.db.scalars(statement))
