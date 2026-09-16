"""Generation job lifecycle with short database transactions around execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.generation.media_generator import MediaGenerator, MediaGeneratorError
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generation_job import (
    GenerationJob,
    GenerationJobEvent,
    GenerationJobEventType,
    GenerationJobKind,
    GenerationJobStatus,
)
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.generation_job_event_repository import GenerationJobEventRepository
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.generation_job import (
    ImageGenerationResult,
    MediaGenerationInput,
    VideoGenerationResult,
)


DEFAULT_MAX_ATTEMPTS = 3


class GenerationJobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.plans = CreativePlanRepository(db)
        self.jobs = GenerationJobRepository(db)
        self.events = GenerationJobEventRepository(db)

    def create_image_job(self, product_id: int, plan_id: int) -> GenerationJob:
        return self._create_job(product_id, plan_id, GenerationJobKind.IMAGE)

    def create_video_job(self, product_id: int, plan_id: int) -> GenerationJob:
        return self._create_job(product_id, plan_id, GenerationJobKind.VIDEO)

    def list(
        self,
        *,
        product_id: int,
        job_kind: GenerationJobKind | None,
        job_status: GenerationJobStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GenerationJob], int]:
        self._require_product(product_id)
        return self.jobs.list_by_product(
            product_id=product_id,
            job_kind=job_kind,
            job_status=job_status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, job_id: int) -> GenerationJob:
        self._require_product(product_id)
        job = self.jobs.get_by_id_and_product_id(job_id, product_id)
        if job is None:
            raise _job_not_found(job_id)
        return job

    def run(
        self,
        *,
        product_id: int,
        job_id: int,
        locked_by: str,
        image_generator: MediaGenerator,
        video_generator: MediaGenerator,
    ) -> GenerationJob:
        self._require_product(product_id)
        job = self.jobs.get_for_update(job_id, product_id)
        if job is None:
            raise _job_not_found(job_id)
        if job.job_status != GenerationJobStatus.PENDING:
            raise _state_conflict(
                f"Job in {job.job_status.value} state cannot be run"
            )
        if job.attempts >= job.max_attempts:
            raise _attempt_limit_error()

        plan = self.plans.get_by_id_and_product_id(
            job.creative_plan_id, product_id
        )
        if plan is None:
            raise _job_not_found(job_id)
        generation_input = MediaGenerationInput(
            job_id=job.id,
            title=plan.title,
            content_json=plan.content_json,
            rationale_text=plan.rationale_text,
        )
        now = _utc_now()
        job.job_status = GenerationJobStatus.RUNNING
        job.attempts += 1
        job.started_at = now
        job.finished_at = None
        job.locked_at = now
        job.locked_by = locked_by
        job.next_run_at = None
        job.result_json = None
        job.error_message = None
        self._add_event(
            job.id,
            GenerationJobEventType.STARTED,
            f"Attempt {job.attempts} started by {locked_by}",
        )
        self._commit()

        generator = (
            image_generator
            if job.job_kind == GenerationJobKind.IMAGE
            else video_generator
        )
        try:
            raw_result = generator.generate(generation_input)
            result_json = _validate_result(job.job_kind, raw_result)
        except MediaGeneratorError as exc:
            return self._finish_failed(
                product_id, job.id, _safe_error_message(str(exc))
            )
        except (ValidationError, TypeError, ValueError):
            return self._finish_failed(
                product_id, job.id, "Generator returned an invalid result"
            )
        except Exception:
            return self._finish_failed(
                product_id, job.id, "Generator execution failed unexpectedly"
            )

        finishing_job = self._require_running_for_finish(product_id, job.id)
        finishing_job.job_status = GenerationJobStatus.SUCCEEDED
        finishing_job.result_json = result_json
        finishing_job.error_message = None
        finishing_job.finished_at = _utc_now()
        finishing_job.locked_at = None
        finishing_job.locked_by = None
        self._add_event(
            finishing_job.id,
            GenerationJobEventType.SUCCEEDED,
            f"Attempt {finishing_job.attempts} succeeded",
        )
        self._commit()
        self.db.refresh(finishing_job)
        return finishing_job

    def retry(self, product_id: int, job_id: int) -> GenerationJob:
        self._require_product(product_id)
        job = self.jobs.get_for_update(job_id, product_id)
        if job is None:
            raise _job_not_found(job_id)
        if job.job_status not in {
            GenerationJobStatus.FAILED,
            GenerationJobStatus.TIMEOUT,
        }:
            raise _state_conflict(
                f"Job in {job.job_status.value} state cannot be retried"
            )
        if job.attempts >= job.max_attempts:
            raise _attempt_limit_error()

        previous_status = job.job_status
        job.job_status = GenerationJobStatus.PENDING
        job.locked_at = None
        job.locked_by = None
        job.next_run_at = None
        job.result_json = None
        job.error_message = None
        job.started_at = None
        job.finished_at = None
        self._add_event(
            job.id,
            GenerationJobEventType.RETRY_REQUESTED,
            f"Retry requested after {previous_status.value}; attempts remain {job.attempts}",
        )
        self._commit()
        self.db.refresh(job)
        return job

    def cancel(self, product_id: int, job_id: int) -> GenerationJob:
        self._require_product(product_id)
        job = self.jobs.get_for_update(job_id, product_id)
        if job is None:
            raise _job_not_found(job_id)
        if job.job_status == GenerationJobStatus.RUNNING:
            raise AppError(
                status_code=409,
                code="running_job_cancellation_not_supported",
                message="Running jobs cannot be force-cancelled by the current executor",
            )
        if job.job_status != GenerationJobStatus.PENDING:
            raise _state_conflict(
                f"Job in {job.job_status.value} state cannot be cancelled"
            )

        job.job_status = GenerationJobStatus.CANCELLED
        job.finished_at = _utc_now()
        job.locked_at = None
        job.locked_by = None
        self._add_event(
            job.id,
            GenerationJobEventType.CANCELLED,
            "Pending job was cancelled",
        )
        self._commit()
        self.db.refresh(job)
        return job

    def sweep_timeouts(self, timeout_seconds: int) -> list[int]:
        cutoff = _utc_now() - timedelta(seconds=timeout_seconds)
        timed_out_jobs = self.jobs.list_timed_out_for_update(cutoff)
        now = _utc_now()
        for job in timed_out_jobs:
            job.job_status = GenerationJobStatus.TIMEOUT
            job.finished_at = now
            job.error_message = f"Generation exceeded {timeout_seconds} seconds"
            job.result_json = None
            job.locked_at = None
            job.locked_by = None
            self._add_event(
                job.id,
                GenerationJobEventType.TIMEOUT,
                f"Running attempt timed out after {timeout_seconds} seconds",
            )
        self._commit()
        return [job.id for job in timed_out_jobs]

    def _create_job(
        self,
        product_id: int,
        plan_id: int,
        job_kind: GenerationJobKind,
    ) -> GenerationJob:
        self._require_product(product_id)
        plan = self.plans.get_for_update_by_id_and_product_id(plan_id, product_id)
        if plan is None:
            raise AppError(
                status_code=404,
                code="creative_plan_not_found",
                message=f"Creative plan {plan_id} was not found for product {product_id}",
            )
        _validate_plan_for_job(plan, job_kind)
        job = GenerationJob(
            product_id=product_id,
            creative_plan_id=plan.id,
            job_kind=job_kind,
            job_status=GenerationJobStatus.PENDING,
            attempts=0,
            max_attempts=DEFAULT_MAX_ATTEMPTS,
        )
        try:
            self.jobs.add(job)
            self.db.flush()
            self._add_event(
                job.id,
                GenerationJobEventType.CREATED,
                f"{job_kind.value} generation job created",
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(job)
        return job

    def _finish_failed(
        self, product_id: int, job_id: int, error_message: str
    ) -> GenerationJob:
        job = self._require_running_for_finish(product_id, job_id)
        job.job_status = GenerationJobStatus.FAILED
        job.result_json = None
        job.error_message = error_message
        job.finished_at = _utc_now()
        job.locked_at = None
        job.locked_by = None
        self._add_event(
            job.id,
            GenerationJobEventType.FAILED,
            f"Attempt {job.attempts} failed: {error_message}",
        )
        self._commit()
        self.db.refresh(job)
        return job

    def _require_running_for_finish(
        self, product_id: int, job_id: int
    ) -> GenerationJob:
        job = self.jobs.get_for_update(job_id, product_id)
        if job is None:
            raise _job_not_found(job_id)
        if job.job_status != GenerationJobStatus.RUNNING:
            raise _state_conflict(
                f"Job changed to {job.job_status.value} before the generator finished"
            )
        return job

    def _require_product(self, product_id: int) -> None:
        if self.products.get_by_id(product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )

    def _add_event(
        self,
        job_id: int,
        event_type: GenerationJobEventType,
        message: str,
    ) -> None:
        self.events.add(
            GenerationJobEvent(
                job_id=job_id,
                event_type=event_type,
                event_message=message,
            )
        )

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise


def _validate_plan_for_job(plan: CreativePlan, job_kind: GenerationJobKind) -> None:
    if plan.status != CreativePlanStatus.SELECTED:
        raise AppError(
            status_code=409,
            code="creative_plan_not_selected",
            message="Only a selected creative plan can create a generation job",
        )
    expected_type = (
        CreativePlanType.MAIN_IMAGE
        if job_kind == GenerationJobKind.IMAGE
        else CreativePlanType.VIDEO_SCRIPT
    )
    if plan.plan_type != expected_type:
        raise AppError(
            status_code=409,
            code="creative_plan_job_kind_mismatch",
            message=f"{plan.plan_type.value} cannot create a {job_kind.value} job",
        )


def _validate_result(
    job_kind: GenerationJobKind, raw_result: dict[str, Any]
) -> dict[str, Any]:
    schema = (
        ImageGenerationResult
        if job_kind == GenerationJobKind.IMAGE
        else VideoGenerationResult
    )
    return schema.model_validate(raw_result).model_dump(mode="json", exclude_none=True)


def _safe_error_message(message: str) -> str:
    stripped = message.strip()
    return stripped[:1000] if stripped else "Generator execution failed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _job_not_found(job_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="generation_job_not_found",
        message=f"Generation job {job_id} was not found",
    )


def _state_conflict(message: str) -> AppError:
    return AppError(
        status_code=409,
        code="invalid_generation_job_state",
        message=message,
    )


def _attempt_limit_error() -> AppError:
    return AppError(
        status_code=409,
        code="generation_job_attempt_limit_reached",
        message="Generation job has reached max_attempts",
    )
