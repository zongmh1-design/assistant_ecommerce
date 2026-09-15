"""Product API ownership, money, status, filters and permissions tests."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus
from app.models.store import Platform, Store
from app.models.user import UserRole


def create_store(
    db: Session,
    *,
    name: str = "商品所属店铺",
    platform: Platform = Platform.TAOBAO,
) -> Store:
    store = Store(store_name=name, platform=platform)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def product_payload(store_id: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "store_id": store_id,
        "name": "训练用商品",
        "platform": "taobao",
        "category": "家居",
        "price": "99.90",
        "cost": "40.25",
        "target_audience": "注重性价比的家庭用户",
        "selling_points": ["耐用", "易清洁"],
        "product_url": "https://example.com/products/1",
        "images_json": ["https://example.com/images/1.jpg"],
        "status": "draft",
    }
    payload.update(overrides)
    return payload


def add_product(
    db: Session,
    *,
    store: Store,
    name: str,
    status: ProductStatus = ProductStatus.DRAFT,
    platform: Platform | None = None,
) -> Product:
    product = Product(
        store_id=store.id,
        name=name,
        platform=platform or store.platform,
        price=Decimal("19.90"),
        cost=Decimal("8.20"),
        selling_points=[],
        images_json=[],
        status=status,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_create_product_with_decimal_money(
    role: UserRole,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)

    response = client.post(
        "/api/v1/products",
        json=product_payload(store.id, price="1234567890.12", cost="0.01"),
        headers=auth_headers_factory(role),
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["price"])) == Decimal("1234567890.12")
    assert Decimal(str(response.json()["cost"])) == Decimal("0.01")
    saved = db_session.get(Product, response.json()["id"])
    assert isinstance(saved.price, Decimal)


def test_viewer_cannot_create_product(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)

    response = client.post(
        "/api/v1/products",
        json=product_payload(store.id),
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 403


def test_create_product_rejects_missing_store(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/products",
        json=product_payload(9999),
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "store_not_found"


def test_product_status_validation(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    response = client.post(
        "/api/v1/products",
        json=product_payload(store.id, status="published"),
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 422


def test_operator_can_update_product_and_clear_nullable_cost(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    product = add_product(db_session, store=store, name="保留名称")

    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"status": "active", "cost": None},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "保留名称"
    assert response.json()["status"] == "active"
    assert response.json()["cost"] is None


def test_viewer_cannot_update_product(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    product = add_product(db_session, store=store, name="只读商品")

    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"name": "不允许修改"},
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 403


def test_product_required_field_rejects_explicit_null(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    product = add_product(db_session, store=store, name="价格不能为空")

    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"price": None},
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 422


def test_filter_products_by_store_id(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    first_store = create_store(db_session, name="店铺一")
    second_store = create_store(db_session, name="店铺二", platform=Platform.JD)
    add_product(db_session, store=first_store, name="商品一")
    add_product(db_session, store=second_store, name="商品二")

    response = client.get(
        f"/api/v1/products?store_id={first_store.id}",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "商品一"


def test_filter_products_by_status(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    add_product(db_session, store=store, name="草稿", status=ProductStatus.DRAFT)
    add_product(db_session, store=store, name="上架", status=ProductStatus.ACTIVE)

    response = client.get(
        "/api/v1/products?status=active",
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "active"


def test_filter_products_by_platform(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    add_product(db_session, store=store, name="淘宝商品", platform=Platform.TAOBAO)
    add_product(db_session, store=store, name="京东商品", platform=Platform.JD)

    response = client.get(
        "/api/v1/products?platform=jd",
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "京东商品"


def test_list_products_for_store_endpoint(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    add_product(db_session, store=store, name="店铺内商品")

    response = client.get(
        f"/api/v1/stores/{store.id}/products",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["store_id"] == store.id


def test_product_list_supports_pagination(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    for index in range(3):
        add_product(db_session, store=store, name=f"商品{index}")

    response = client.get(
        "/api/v1/products?page=2&page_size=1",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert len(response.json()["items"]) == 1


def test_update_product_rejects_missing_store(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = create_store(db_session)
    product = add_product(db_session, store=store, name="不能移动")

    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"store_id": 9999},
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 404


def test_query_missing_product_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.get(
        "/api/v1/products/9999",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"
