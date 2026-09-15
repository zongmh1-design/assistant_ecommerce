"""Inventory initialization, adjustment, history, permissions and rollback tests."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, InventoryMovement
from app.models.product import Product
from app.models.product_sku import ProductSku, ProductSkuStatus
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.schemas.inventory import InventoryAdjustment
from app.schemas.product_sku import ProductSkuCreate
from app.services.inventory_service import InventoryService
from app.services.product_sku_service import ProductSkuService


def create_sku_with_inventory(
    db: Session,
    *,
    status: ProductSkuStatus = ProductSkuStatus.ACTIVE,
) -> ProductSku:
    store = Store(store_name="库存测试店铺", platform=Platform.JD)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name="库存测试商品",
        platform=Platform.JD,
        price=Decimal("50.00"),
        selling_points=[],
        images_json=[],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductSkuService(db).create(
        product.id,
        ProductSkuCreate(
            sku_code="DEFAULT",
            sku_name="默认规格",
            spec_json={},
            price=Decimal("50.00"),
            status=status,
        ),
    )


def test_sku_creation_initializes_inventory_and_initial_movement(
    db_session: Session,
) -> None:
    sku = create_sku_with_inventory(db_session)

    inventory = db_session.scalar(
        select(InventoryItem).where(InventoryItem.sku_id == sku.id)
    )
    movements = list(
        db_session.scalars(
            select(InventoryMovement).where(InventoryMovement.sku_id == sku.id)
        )
    )

    assert inventory is not None
    assert inventory.stock_qty == 0
    assert inventory.locked_qty == 0
    assert inventory.warning_threshold == 0
    assert inventory.available_qty == 0
    assert len(movements) == 1
    assert movements[0].movement_type.value == "initial"
    assert movements[0].change_qty == 0


def test_normal_inbound_updates_inventory_and_creates_movement(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)

    response = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": 10, "reason_text": "采购入库"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    assert response.json()["stock_qty"] == 10
    assert response.json()["available_qty"] == 10
    movement = db_session.scalar(
        select(InventoryMovement)
        .where(InventoryMovement.sku_id == sku.id)
        .order_by(InventoryMovement.id.desc())
    )
    assert movement.movement_type.value == "inbound"
    assert movement.before_qty == 0
    assert movement.change_qty == 10
    assert movement.after_qty == 10


def test_normal_outbound_keeps_stock_and_movement_consistent(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    inbound = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": 20, "reason_text": "首次入库"},
        headers=headers,
    )
    assert inbound.status_code == 200

    outbound = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": -5, "reason_text": "人工出库"},
        headers=headers,
    )

    assert outbound.status_code == 200
    assert outbound.json()["stock_qty"] == 15
    movement = db_session.scalar(
        select(InventoryMovement)
        .where(InventoryMovement.sku_id == sku.id)
        .order_by(InventoryMovement.id.desc())
    )
    assert movement.movement_type.value == "outbound"
    assert movement.before_qty == 20
    assert movement.change_qty == -5
    assert movement.after_qty == 15


def test_insufficient_stock_does_not_change_inventory_or_add_movement(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)

    response = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": -1, "reason_text": "库存不足出库"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 409
    inventory = db_session.scalar(
        select(InventoryItem).where(InventoryItem.sku_id == sku.id)
    )
    movement_count = db_session.scalar(
        select(func.count())
        .select_from(InventoryMovement)
        .where(InventoryMovement.sku_id == sku.id)
    )
    assert inventory.stock_qty == 0
    assert movement_count == 1


def test_inventory_settings_update_without_direct_stock_patch(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)

    response = client.patch(
        f"/api/v1/skus/{sku.id}/inventory/settings",
        json={"warning_threshold": 8, "location_text": "A-01"},
        headers=headers,
    )
    cleared = client.patch(
        f"/api/v1/skus/{sku.id}/inventory/settings",
        json={"location_text": None},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["warning_threshold"] == 8
    assert response.json()["stock_qty"] == 0
    assert cleared.status_code == 200
    assert cleared.json()["warning_threshold"] == 8
    assert cleared.json()["location_text"] is None


def test_inventory_settings_rejects_direct_stock_qty_patch(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)

    response = client.patch(
        f"/api/v1/skus/{sku.id}/inventory/settings",
        json={"stock_qty": 500},
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 422
    inventory = InventoryService(db_session).get(sku.id)
    assert inventory.stock_qty == 0


def test_viewer_cannot_adjust_inventory(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)

    response = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": 1, "reason_text": "不允许的入库"},
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 403


def test_viewer_can_query_inventory_and_paginated_movements(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session)
    admin_headers = auth_headers_factory(UserRole.ADMIN)
    viewer_headers = auth_headers_factory(UserRole.VIEWER)
    client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": 3, "reason_text": "入库"},
        headers=admin_headers,
    )

    inventory_response = client.get(
        f"/api/v1/skus/{sku.id}/inventory",
        headers=viewer_headers,
    )
    movements_response = client.get(
        f"/api/v1/skus/{sku.id}/inventory/movements?page=1&page_size=1",
        headers=viewer_headers,
    )

    assert inventory_response.status_code == 200
    assert inventory_response.json()["stock_qty"] == 3
    assert movements_response.status_code == 200
    assert movements_response.json()["total"] == 2
    assert len(movements_response.json()["items"]) == 1
    assert movements_response.json()["items"][0]["movement_type"] == "inbound"


def test_missing_sku_inventory_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.get(
        "/api/v1/skus/9999/inventory",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sku_not_found"


def test_inventory_and_movement_roll_back_together_when_movement_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sku = create_sku_with_inventory(db_session)
    service = InventoryService(db_session)

    def fail_to_add_movement(_: InventoryMovement) -> InventoryMovement:
        raise RuntimeError("simulated movement write failure")

    monkeypatch.setattr(service.inventory, "add_movement", fail_to_add_movement)

    with pytest.raises(RuntimeError, match="simulated movement write failure"):
        service.adjust(
            sku.id,
            InventoryAdjustment(change_qty=7, reason_text="事务回滚测试"),
        )

    inventory = service.get(sku.id)
    movement_count = db_session.scalar(
        select(func.count())
        .select_from(InventoryMovement)
        .where(InventoryMovement.sku_id == sku.id)
    )
    assert inventory.stock_qty == 0
    assert movement_count == 1


def test_inactive_sku_inventory_is_read_only(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    sku = create_sku_with_inventory(db_session, status=ProductSkuStatus.INACTIVE)
    headers = auth_headers_factory(UserRole.ADMIN)

    read_response = client.get(
        f"/api/v1/skus/{sku.id}/inventory",
        headers=headers,
    )
    adjust_response = client.post(
        f"/api/v1/skus/{sku.id}/inventory/adjust",
        json={"change_qty": 1, "reason_text": "停用后入库"},
        headers=headers,
    )
    settings_response = client.patch(
        f"/api/v1/skus/{sku.id}/inventory/settings",
        json={"warning_threshold": 1},
        headers=headers,
    )

    assert read_response.status_code == 200
    assert adjust_response.status_code == 409
    assert settings_response.status_code == 409
    assert adjust_response.json()["error"]["code"] == "sku_inactive"
