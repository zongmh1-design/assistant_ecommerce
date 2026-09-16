"""Creative plan generation, query and editing endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.creative_plan import CreativePlanStatus, CreativePlanType
from app.models.user import User
from app.schemas.creative_plan import (
    CreativePlanListResponse,
    CreativePlanRead,
    CreativePlanUpdate,
)
from app.services.creative_plan_service import CreativePlanService


router = APIRouter(tags=["creative-plans"])
ProviderDependency = Annotated[LLMProvider, Depends(get_llm_provider)]


@router.post(
    "/products/{product_id}/creative-plans/main-images/generate",
    response_model=list[CreativePlanRead],
    status_code=201,
)
def generate_main_image_plans(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    provider: ProviderDependency,
) -> list[CreativePlanRead]:
    return CreativePlanService(db).generate_main_images(product_id, provider)


@router.post(
    "/products/{product_id}/creative-plans/video-scripts/generate",
    response_model=list[CreativePlanRead],
    status_code=201,
)
def generate_video_scripts(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    provider: ProviderDependency,
) -> list[CreativePlanRead]:
    return CreativePlanService(db).generate_video_scripts(product_id, provider)


@router.get(
    "/products/{product_id}/creative-plans",
    response_model=CreativePlanListResponse,
)
def list_creative_plans(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    plan_type: Annotated[CreativePlanType | None, Query()] = None,
    status: Annotated[CreativePlanStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CreativePlanListResponse:
    items, total = CreativePlanService(db).list(
        product_id=product_id,
        plan_type=plan_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return CreativePlanListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_id}/creative-plans/{creative_plan_id}",
    response_model=CreativePlanRead,
)
def get_creative_plan(
    product_id: Annotated[int, Path(gt=0)],
    creative_plan_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CreativePlanRead:
    return CreativePlanService(db).get(product_id, creative_plan_id)


@router.patch(
    "/products/{product_id}/creative-plans/{creative_plan_id}",
    response_model=CreativePlanRead,
)
def update_creative_plan(
    product_id: Annotated[int, Path(gt=0)],
    creative_plan_id: Annotated[int, Path(gt=0)],
    payload: CreativePlanUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> CreativePlanRead:
    return CreativePlanService(db).update(product_id, creative_plan_id, payload)
