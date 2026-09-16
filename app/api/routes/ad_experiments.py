"""Generate, edit, query and manually transition advertising experiments."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.ad_experiment import AdExperimentStatus
from app.models.user import User
from app.schemas.ad_experiment import (
    AdExperimentGenerate, AdExperimentListResponse, AdExperimentRead,
    AdExperimentStatusUpdate, AdExperimentUpdate,
)
from app.services.ad_experiment_service import AdExperimentService


router = APIRouter(tags=["ad-experiments"])


@router.post(
    "/products/{product_id}/ad-experiments/generate",
    response_model=AdExperimentRead,
)
def generate_ad_experiment(
    product_id: Annotated[int, Path(gt=0)], payload: AdExperimentGenerate,
    _: Annotated[User, Depends(require_write_access)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> AdExperimentRead:
    return AdExperimentService(db).generate(product_id, payload, provider)


@router.get(
    "/products/{product_id}/ad-experiments",
    response_model=AdExperimentListResponse,
)
def list_ad_experiments(
    product_id: Annotated[int, Path(gt=0)], _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    experiment_status: Annotated[AdExperimentStatus | None, Query()] = None,
    ad_recommendation_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdExperimentListResponse:
    items, total = AdExperimentService(db).list(
        product_id=product_id, experiment_status=experiment_status,
        ad_recommendation_id=ad_recommendation_id, page=page, page_size=page_size,
    )
    return AdExperimentListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get(
    "/products/{product_id}/ad-experiments/{experiment_id}",
    response_model=AdExperimentRead,
)
def get_ad_experiment(
    product_id: Annotated[int, Path(gt=0)], experiment_id: Annotated[int, Path(gt=0)],
    _: CurrentUser, db: Annotated[Session, Depends(get_db)],
) -> AdExperimentRead:
    return AdExperimentService(db).get(product_id, experiment_id)


@router.patch(
    "/products/{product_id}/ad-experiments/{experiment_id}",
    response_model=AdExperimentRead,
)
def update_ad_experiment(
    product_id: Annotated[int, Path(gt=0)], experiment_id: Annotated[int, Path(gt=0)],
    payload: AdExperimentUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> AdExperimentRead:
    return AdExperimentService(db).update(product_id, experiment_id, payload)


@router.patch(
    "/products/{product_id}/ad-experiments/{experiment_id}/status",
    response_model=AdExperimentRead,
)
def update_ad_experiment_status(
    product_id: Annotated[int, Path(gt=0)], experiment_id: Annotated[int, Path(gt=0)],
    payload: AdExperimentStatusUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> AdExperimentRead:
    return AdExperimentService(db).update_status(product_id, experiment_id, payload)
