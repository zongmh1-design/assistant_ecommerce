"""Store REST endpoints for Phase 2A."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.product import ProductListResponse
from app.schemas.store import StoreCreate, StoreListResponse, StoreRead, StoreUpdate
from app.services.product_service import ProductService
from app.services.store_service import StoreService


router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("", response_model=StoreRead, status_code=201)
def create_store(
    payload: StoreCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> StoreRead:
    return StoreService(db).create(payload)


@router.get("", response_model=StoreListResponse)
def list_stores(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StoreListResponse:
    items, total = StoreService(db).list(page=page, page_size=page_size)
    return StoreListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{store_id}", response_model=StoreRead)
def get_store(
    store_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> StoreRead:
    return StoreService(db).get(store_id)


@router.patch("/{store_id}", response_model=StoreRead)
def update_store(
    store_id: Annotated[int, Path(gt=0)],
    payload: StoreUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> StoreRead:
    return StoreService(db).update(store_id, payload)


@router.get("/{store_id}/products", response_model=ProductListResponse)
def list_store_products(
    store_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductListResponse:
    items, total = ProductService(db).list(
        page=page,
        page_size=page_size,
        store_id=store_id,
        require_store=True,
    )
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
