"""Product REST endpoints and simple Phase 2A filters."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.product import ProductStatus
from app.models.store import Platform
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from app.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return ProductService(db).create(payload)


@router.get("", response_model=ProductListResponse)
def list_products(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    store_id: Annotated[int | None, Query(gt=0)] = None,
    platform: Annotated[Platform | None, Query()] = None,
    status: Annotated[ProductStatus | None, Query()] = None,
) -> ProductListResponse:
    items, total = ProductService(db).list(
        page=page,
        page_size=page_size,
        store_id=store_id,
        platform=platform,
        status=status,
    )
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return ProductService(db).get(product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: Annotated[int, Path(gt=0)],
    payload: ProductUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return ProductService(db).update(product_id, payload)
