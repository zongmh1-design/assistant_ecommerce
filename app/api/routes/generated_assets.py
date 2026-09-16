"""Synchronize, query and manually review generated assets."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.generated_asset import AssetReviewStatus, GeneratedAssetType
from app.models.user import User
from app.schemas.generated_asset import (
    AssetSyncResult,
    GeneratedAssetListResponse,
    GeneratedAssetRead,
    GeneratedAssetUpdate,
)
from app.services.generated_asset_service import GeneratedAssetService


router = APIRouter(tags=["generated-assets"])


@router.post(
    "/products/{product_id}/assets/sync",
    response_model=AssetSyncResult,
)
def sync_generated_assets(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> AssetSyncResult:
    return GeneratedAssetService(db).sync_succeeded_jobs(product_id)


@router.get(
    "/products/{product_id}/assets",
    response_model=GeneratedAssetListResponse,
)
def list_generated_assets(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    asset_type: Annotated[GeneratedAssetType | None, Query()] = None,
    review_status: Annotated[AssetReviewStatus | None, Query()] = None,
    creative_plan_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GeneratedAssetListResponse:
    items, total = GeneratedAssetService(db).list(
        product_id=product_id,
        asset_type=asset_type,
        review_status=review_status,
        creative_plan_id=creative_plan_id,
        page=page,
        page_size=page_size,
    )
    return GeneratedAssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_id}/assets/{asset_id}",
    response_model=GeneratedAssetRead,
)
def get_generated_asset(
    product_id: Annotated[int, Path(gt=0)],
    asset_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> GeneratedAssetRead:
    return GeneratedAssetService(db).get(product_id, asset_id)


@router.patch(
    "/products/{product_id}/assets/{asset_id}",
    response_model=GeneratedAssetRead,
)
def update_generated_asset(
    product_id: Annotated[int, Path(gt=0)],
    asset_id: Annotated[int, Path(gt=0)],
    payload: GeneratedAssetUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> GeneratedAssetRead:
    return GeneratedAssetService(db).update(product_id, asset_id, payload)
