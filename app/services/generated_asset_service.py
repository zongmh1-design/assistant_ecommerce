"""Synchronize validated job results into reviewable business assets."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.generated_asset import (
    AssetReviewStatus,
    GeneratedAsset,
    GeneratedAssetType,
)
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.generated_asset import (
    AssetSyncFailure,
    AssetSyncResult,
    GeneratedAssetUpdate,
)
from app.schemas.generation_job import ImageGenerationResult, VideoGenerationResult


class InvalidGenerationResultError(Exception):
    """A succeeded job has no result payload to validate."""


class GeneratedAssetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.plans = CreativePlanRepository(db)
        self.jobs = GenerationJobRepository(db)
        self.assets = GeneratedAssetRepository(db)

    def sync_succeeded_jobs(self, product_id: int) -> AssetSyncResult:
        self._require_product(product_id)
        job_ids = self.jobs.list_succeeded_ids_by_product(product_id)
        self.db.commit()

        asset_ids: list[int] = []
        failures: list[AssetSyncFailure] = []
        skipped_count = 0
        for job_id in job_ids:
            outcome, value = self._sync_one(product_id, job_id)
            if outcome == "synced":
                asset_ids.append(value)
            elif outcome == "skipped":
                skipped_count += 1
            else:
                failures.append(value)
        return AssetSyncResult(
            synced_count=len(asset_ids),
            skipped_count=skipped_count,
            failed_count=len(failures),
            asset_ids=asset_ids,
            failures=failures,
        )

    def list(
        self,
        *,
        product_id: int,
        asset_type: GeneratedAssetType | None,
        review_status: AssetReviewStatus | None,
        creative_plan_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GeneratedAsset], int]:
        self._require_product(product_id)
        return self.assets.list_by_product(
            product_id=product_id,
            asset_type=asset_type,
            review_status=review_status,
            creative_plan_id=creative_plan_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, asset_id: int) -> GeneratedAsset:
        self._require_product(product_id)
        asset = self.assets.get_by_id_and_product_id(asset_id, product_id)
        if asset is None:
            raise _asset_not_found(asset_id)
        return asset

    def update(
        self,
        product_id: int,
        asset_id: int,
        payload: GeneratedAssetUpdate,
    ) -> GeneratedAsset:
        asset = self.get(product_id, asset_id)
        changes = payload.model_dump(exclude_unset=True)
        desired_status = changes.get("review_status")
        if desired_status is not None and desired_status != asset.review_status:
            _validate_review_transition(asset.review_status, desired_status)
        for field_name, value in changes.items():
            setattr(asset, field_name, value)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(asset)
        return asset

    def _sync_one(
        self, product_id: int, job_id: int
    ) -> tuple[str, int | AssetSyncFailure]:
        try:
            job = self.jobs.get_for_update(job_id, product_id)
            if job is None or job.job_status != GenerationJobStatus.SUCCEEDED:
                self.db.commit()
                return "skipped", job_id
            if self.assets.get_by_job_id(job.id) is not None:
                self.db.commit()
                return "skipped", job_id

            result = _validate_job_result(job)
            plan = self.plans.get_for_update_by_id_and_product_id(
                job.creative_plan_id, product_id
            )
            if plan is None:
                self.db.rollback()
                return "failed", _failure(
                    job.id,
                    "creative_plan_not_found",
                    "Source creative plan was not found",
                )
            asset_type = GeneratedAssetType(job.job_kind.value)
            version_no = self.assets.next_version_no(
                product_id=product_id,
                creative_plan_id=plan.id,
                asset_type=asset_type,
            )
            asset = _build_asset(job, result, asset_type, version_no)
            self.assets.add(asset)
            self.db.commit()
            self.db.refresh(asset)
            return "synced", asset.id
        except (InvalidGenerationResultError, ValidationError):
            self.db.rollback()
            return "failed", _failure(
                job_id,
                "invalid_generation_result",
                "Succeeded job result does not match its media schema",
            )
        except IntegrityError:
            self.db.rollback()
            if self.assets.get_by_job_id(job_id) is not None:
                self.db.commit()
                return "skipped", job_id
            self.db.rollback()
            return "failed", _failure(
                job_id,
                "asset_version_conflict",
                "Asset version allocation conflicted; retry synchronization",
            )
        except Exception:
            self.db.rollback()
            return "failed", _failure(
                job_id,
                "asset_persistence_error",
                "Asset could not be persisted",
            )

    def _require_product(self, product_id: int) -> None:
        if self.products.get_by_id(product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )


def _validate_job_result(
    job: GenerationJob,
) -> ImageGenerationResult | VideoGenerationResult:
    if job.result_json is None:
        raise InvalidGenerationResultError("result_json is missing")
    schema = (
        ImageGenerationResult
        if job.job_kind == GenerationJobKind.IMAGE
        else VideoGenerationResult
    )
    return schema.model_validate(job.result_json)


def _build_asset(
    job: GenerationJob,
    result: ImageGenerationResult | VideoGenerationResult,
    asset_type: GeneratedAssetType,
    version_no: int,
) -> GeneratedAsset:
    common: dict[str, Any] = {
        "product_id": job.product_id,
        "creative_plan_id": job.creative_plan_id,
        "generation_job_id": job.id,
        "asset_type": asset_type,
        "asset_url": result.url,
        "model_name": result.model_name or result.generator,
        "review_status": AssetReviewStatus.PENDING,
        "version_no": version_no,
        "tags_json": [],
    }
    if isinstance(result, ImageGenerationResult):
        common.update(width=result.width, height=result.height, duration_sec=None)
    else:
        common.update(width=None, height=None, duration_sec=result.duration_sec)
    return GeneratedAsset(**common)


def _failure(job_id: int, code: str, message: str) -> AssetSyncFailure:
    return AssetSyncFailure(job_id=job_id, code=code, message=message)


def _asset_not_found(asset_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="generated_asset_not_found",
        message=f"Generated asset {asset_id} was not found",
    )


def _validate_review_transition(
    current: AssetReviewStatus, desired: AssetReviewStatus
) -> None:
    allowed = {
        AssetReviewStatus.PENDING: {
            AssetReviewStatus.APPROVED,
            AssetReviewStatus.REJECTED,
        },
        AssetReviewStatus.APPROVED: {AssetReviewStatus.REJECTED},
        AssetReviewStatus.REJECTED: {AssetReviewStatus.APPROVED},
    }
    if desired not in allowed[current]:
        raise AppError(
            status_code=409,
            code="invalid_asset_review_status_transition",
            message=f"Cannot change asset review from {current.value} to {desired.value}",
        )
