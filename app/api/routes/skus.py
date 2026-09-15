"""Product SKU REST endpoints for Phase 2B."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.product_sku import (
    ProductSkuCreate,
    ProductSkuListResponse,
    ProductSkuRead,
    ProductSkuUpdate,
)
from app.services.product_sku_service import ProductSkuService


router = APIRouter(tags=["skus"])


@router.post("/products/{product_id}/skus", response_model=ProductSkuRead, status_code=201)
def create_sku(
    product_id: Annotated[int, Path(gt=0)],
    payload: ProductSkuCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductSkuRead:
    return ProductSkuService(db).create(product_id, payload)


@router.get("/products/{product_id}/skus", response_model=ProductSkuListResponse)
def list_product_skus(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductSkuListResponse:
    items, total = ProductSkuService(db).list(
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
    return ProductSkuListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/skus/{sku_id}", response_model=ProductSkuRead)
def get_sku(
    sku_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ProductSkuRead:
    return ProductSkuService(db).get(sku_id)


@router.patch("/skus/{sku_id}", response_model=ProductSkuRead)
def update_sku(
    sku_id: Annotated[int, Path(gt=0)],
    payload: ProductSkuUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductSkuRead:
    return ProductSkuService(db).update(sku_id, payload)
