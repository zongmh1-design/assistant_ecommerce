"""Current inventory, adjustment, settings and movement REST endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.inventory import (
    InventoryAdjustment,
    InventoryMovementListResponse,
    InventoryRead,
    InventorySettingsUpdate,
)
from app.services.inventory_service import InventoryService


router = APIRouter(prefix="/skus/{sku_id}/inventory", tags=["inventory"])


@router.get("", response_model=InventoryRead)
def get_inventory(
    sku_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> InventoryRead:
    return InventoryService(db).get(sku_id)


@router.post("/adjust", response_model=InventoryRead)
def adjust_inventory(
    sku_id: Annotated[int, Path(gt=0)],
    payload: InventoryAdjustment,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> InventoryRead:
    return InventoryService(db).adjust(sku_id, payload)


@router.patch("/settings", response_model=InventoryRead)
def update_inventory_settings(
    sku_id: Annotated[int, Path(gt=0)],
    payload: InventorySettingsUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> InventoryRead:
    return InventoryService(db).update_settings(sku_id, payload)


@router.get("/movements", response_model=InventoryMovementListResponse)
def list_inventory_movements(
    sku_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InventoryMovementListResponse:
    items, total = InventoryService(db).list_movements(
        sku_id=sku_id,
        page=page,
        page_size=page_size,
    )
    return InventoryMovementListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
