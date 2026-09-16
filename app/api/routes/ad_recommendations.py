"""Generate, edit, query and make final human decisions on ad advice."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.ad_recommendation import AdRecommendationConfirmStatus
from app.models.user import User
from app.schemas.ad_recommendation import (
    AdRecommendationConfirmation, AdRecommendationListResponse,
    AdRecommendationRead, AdRecommendationUpdate,
)
from app.services.ad_recommendation_service import AdRecommendationService


router = APIRouter(tags=["ad-recommendations"])


@router.post(
    "/products/{product_id}/ad-recommendations/generate",
    response_model=AdRecommendationRead,
)
def generate_ad_recommendation(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> AdRecommendationRead:
    return AdRecommendationService(db).generate(product_id, provider)


@router.get(
    "/products/{product_id}/ad-recommendations",
    response_model=AdRecommendationListResponse,
)
def list_ad_recommendations(
    product_id: Annotated[int, Path(gt=0)], _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    confirm_status: Annotated[AdRecommendationConfirmStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdRecommendationListResponse:
    items, total = AdRecommendationService(db).list(
        product_id=product_id, confirm_status=confirm_status,
        page=page, page_size=page_size,
    )
    return AdRecommendationListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get(
    "/products/{product_id}/ad-recommendations/{recommendation_id}",
    response_model=AdRecommendationRead,
)
def get_ad_recommendation(
    product_id: Annotated[int, Path(gt=0)], recommendation_id: Annotated[int, Path(gt=0)],
    _: CurrentUser, db: Annotated[Session, Depends(get_db)],
) -> AdRecommendationRead:
    return AdRecommendationService(db).get(product_id, recommendation_id)


@router.patch(
    "/products/{product_id}/ad-recommendations/{recommendation_id}",
    response_model=AdRecommendationRead,
)
def update_ad_recommendation(
    product_id: Annotated[int, Path(gt=0)], recommendation_id: Annotated[int, Path(gt=0)],
    payload: AdRecommendationUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> AdRecommendationRead:
    return AdRecommendationService(db).update(product_id, recommendation_id, payload)


@router.patch(
    "/products/{product_id}/ad-recommendations/{recommendation_id}/confirmation",
    response_model=AdRecommendationRead,
)
def confirm_ad_recommendation(
    product_id: Annotated[int, Path(gt=0)], recommendation_id: Annotated[int, Path(gt=0)],
    payload: AdRecommendationConfirmation,
    current_user: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> AdRecommendationRead:
    return AdRecommendationService(db).confirm(
        product_id, recommendation_id, payload, current_user.id
    )
