"""ProductSku API ownership, uniqueness, money, status and permissions tests."""

from collections.abc import Callable
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.store import Platform, Store
from app.models.user import UserRole


def create_product(db: Session, *, name: str = "SKU 所属商品") -> Product:
    store = Store(store_name=f"{name}店铺", platform=Platform.TAOBAO)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=name,
        platform=Platform.TAOBAO,
        price=Decimal("99.00"),
        cost=Decimal("30.00"),
        selling_points=[],
        images_json=[],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def sku_payload(code: str = "RED-L", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sku_code": code,
        "sku_name": "红色 L",
        "spec_json": {"color": "red", "size": "L"},
        "price": "109.90",
        "cost": "39.25",
        "status": "active",
        "platform_sku_id": None,
    }
    payload.update(overrides)
    return payload


def test_create_sku_success_with_decimal_money(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)

    response = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(price="1234567890.12", cost="0.01"),
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 201
    assert response.json()["product_id"] == product.id
    assert Decimal(str(response.json()["price"])) == Decimal("1234567890.12")
    assert Decimal(str(response.json()["cost"])) == Decimal("0.01")


def test_create_sku_for_missing_product_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/products/9999/skus",
        json=sku_payload(),
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


def test_duplicate_sku_code_in_same_product_is_rejected(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(),
        headers=headers,
    )

    second = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(),
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "sku_code_conflict"


def test_same_sku_code_is_allowed_for_different_products(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    first_product = create_product(db_session, name="商品一")
    second_product = create_product(db_session, name="商品二")
    headers = auth_headers_factory(UserRole.OPERATOR)

    first = client.post(
        f"/api/v1/products/{first_product.id}/skus",
        json=sku_payload(),
        headers=headers,
    )
    second = client.post(
        f"/api/v1/products/{second_product.id}/skus",
        json=sku_payload(),
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_sku_status_validation(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)

    response = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(status="archived"),
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 422


def test_operator_can_update_sku_and_clear_nullable_cost(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    created = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(),
        headers=headers,
    )

    response = client.patch(
        f"/api/v1/skus/{created.json()['id']}",
        json={"sku_name": "红色大码", "cost": None, "status": "inactive"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["sku_name"] == "红色大码"
    assert response.json()["sku_code"] == "RED-L"
    assert response.json()["cost"] is None
    assert response.json()["status"] == "inactive"


def test_viewer_cannot_create_or_update_sku(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)
    admin_headers = auth_headers_factory(UserRole.ADMIN)
    viewer_headers = auth_headers_factory(UserRole.VIEWER)
    created = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(),
        headers=admin_headers,
    )

    create_response = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload("RED-XL"),
        headers=viewer_headers,
    )
    update_response = client.patch(
        f"/api/v1/skus/{created.json()['id']}",
        json={"sku_name": "不允许修改"},
        headers=viewer_headers,
    )

    assert create_response.status_code == 403
    assert update_response.status_code == 403


def test_viewer_can_list_and_get_product_skus(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = create_product(db_session)
    admin_headers = auth_headers_factory(UserRole.ADMIN)
    viewer_headers = auth_headers_factory(UserRole.VIEWER)
    created = client.post(
        f"/api/v1/products/{product.id}/skus",
        json=sku_payload(),
        headers=admin_headers,
    )
    sku_id = created.json()["id"]

    list_response = client.get(
        f"/api/v1/products/{product.id}/skus",
        headers=viewer_headers,
    )
    detail_response = client.get(
        f"/api/v1/skus/{sku_id}",
        headers=viewer_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["sku_code"] == "RED-L"
