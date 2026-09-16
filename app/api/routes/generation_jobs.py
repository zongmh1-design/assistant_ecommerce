"""Create, execute and inspect media generation jobs."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_admin, require_write_access
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.generation.dependencies import get_image_generator, get_video_generator
from app.generation.media_generator import MediaGenerator
from app.models.generation_job import GenerationJobKind, GenerationJobStatus
from app.models.user import User
from app.schemas.generation_job import (
    GenerationJobDetail,
    GenerationJobListResponse,
    GenerationJobRead,
    TimeoutSweepResponse,
)
from app.services.generation_job_service import GenerationJobService


router = APIRouter(tags=["generation-jobs"])
ImageGeneratorDependency = Annotated[MediaGenerator, Depends(get_image_generator)]
VideoGeneratorDependency = Annotated[MediaGenerator, Depends(get_video_generator)]


@router.post(
    "/products/{product_id}/creative-plans/{creative_plan_id}/images/generate",
    response_model=GenerationJobRead,
    status_code=201,
)
def create_image_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    creative_plan_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationJobRead:
    return GenerationJobService(db).create_image_job(product_id, creative_plan_id)


@router.post(
    "/products/{product_id}/creative-plans/{creative_plan_id}/videos/generate",
    response_model=GenerationJobRead,
    status_code=201,
)
def create_video_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    creative_plan_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationJobRead:
    return GenerationJobService(db).create_video_job(product_id, creative_plan_id)


@router.get(
    "/products/{product_id}/generation-jobs",
    response_model=GenerationJobListResponse,
)
def list_generation_jobs(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    job_kind: Annotated[GenerationJobKind | None, Query()] = None,
    job_status: Annotated[GenerationJobStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GenerationJobListResponse:
    items, total = GenerationJobService(db).list(
        product_id=product_id,
        job_kind=job_kind,
        job_status=job_status,
        page=page,
        page_size=page_size,
    )
    return GenerationJobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_id}/generation-jobs/{job_id}",
    response_model=GenerationJobDetail,
)
def get_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    job_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> GenerationJobDetail:
    return GenerationJobService(db).get(product_id, job_id)


@router.post(
    "/products/{product_id}/generation-jobs/{job_id}/run",
    response_model=GenerationJobDetail,
)
def run_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    job_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    image_generator: ImageGeneratorDependency,
    video_generator: VideoGeneratorDependency,
) -> GenerationJobDetail:
    return GenerationJobService(db).run(
        product_id=product_id,
        job_id=job_id,
        locked_by=f"manual-runner:user-{current_user.id}",
        image_generator=image_generator,
        video_generator=video_generator,
    )


@router.post(
    "/products/{product_id}/generation-jobs/{job_id}/retry",
    response_model=GenerationJobDetail,
)
def retry_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    job_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationJobDetail:
    return GenerationJobService(db).retry(product_id, job_id)


@router.post(
    "/products/{product_id}/generation-jobs/{job_id}/cancel",
    response_model=GenerationJobDetail,
)
def cancel_generation_job(
    product_id: Annotated[int, Path(gt=0)],
    job_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationJobDetail:
    return GenerationJobService(db).cancel(product_id, job_id)


@router.post(
    "/workspace/generation-jobs/sweep-timeouts",
    response_model=TimeoutSweepResponse,
)
def sweep_generation_job_timeouts(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TimeoutSweepResponse:
    job_ids = GenerationJobService(db).sweep_timeouts(
        settings.generation_job_timeout_seconds
    )
    return TimeoutSweepResponse(timed_out_count=len(job_ids), job_ids=job_ids)
