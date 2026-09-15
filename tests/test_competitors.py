"""Competitor manual-entry, ownership, money and permission tests."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.competitor import Competitor
from app.models.product import Product, ProductStatus
from app.models.store import Platform, Store
from app.models.user import UserRole


def add_product(db: Session, *, name: str = "竞品所属商品") -> Product:
    store = Store(store_name=f"{name}店铺", platform=Platform.TAOBAO)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=name,
        platform=Platform.TAOBAO,
        price=Decimal("99.00"),
        selling_points=[],
        images_json=[],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def competitor_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "轻量竞品",
        "platform": "jd",
        "url": "https://example.com/products/competitor-001",
        "price": "59.90",
        "sales_hint": "公开页面展示月销 100+",
        "title": "轻量耐用竞品标题",
        "main_image": "https://example.com/images/competitor-001.jpg",
        "selling_points": ["轻量化", "续航长"],
        "review_keywords": ["质量", "物流"],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_can_create_competitor_with_decimal_price(
    role: UserRole,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = client.post(
        f"/api/v1/products/{product.id}/competitors",
        json=competitor_payload(price="1234567890.12"),
        headers=auth_headers_factory(role),
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["price"])) == Decimal("1234567890.12")
    saved = db_session.get(Competitor, response.json()["id"])
    assert isinstance(saved.price, Decimal)


def test_missing_product_cannot_receive_competitor(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/products/9999/competitors",
        json=competitor_payload(),
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


def test_viewer_can_read_but_cannot_write_competitor(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = client.post(
        f"/api/v1/products/{product.id}/competitors",
        json=competitor_payload(),
        headers=auth_headers_factory(UserRole.ADMIN),
    ).json()
    viewer_headers = auth_headers_factory(UserRole.VIEWER)

    assert client.get(
        f"/api/v1/competitors/{created['id']}", headers=viewer_headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/products/{product.id}/competitors",
        json=competitor_payload(name="禁止创建"),
        headers=viewer_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/v1/competitors/{created['id']}",
        json={"name": "禁止修改"},
        headers=viewer_headers,
    ).status_code == 403


def test_product_competitor_list_supports_pagination(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    for index in range(3):
        response = client.post(
            f"/api/v1/products/{product.id}/competitors",
            json=competitor_payload(name=f"竞品{index}"),
            headers=headers,
        )
        assert response.status_code == 201

    response = client.get(
        f"/api/v1/products/{product.id}/competitors?page=2&page_size=1",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert len(response.json()["items"]) == 1


def test_operator_can_patch_competitor_and_clear_nullable_fields(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = client.post(
        f"/api/v1/products/{product.id}/competitors",
        json=competitor_payload(),
        headers=auth_headers_factory(UserRole.ADMIN),
    ).json()

    response = client.patch(
        f"/api/v1/competitors/{created['id']}",
        json={"name": "修改后竞品", "price": None, "sales_hint": None},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "修改后竞品"
    assert response.json()["price"] is None
    assert response.json()["sales_hint"] is None


def test_missing_competitor_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.get(
        "/api/v1/competitors/9999",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "competitor_not_found"
