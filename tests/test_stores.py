"""Store API permissions, pagination, PATCH and not-found behavior."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.store import Platform, Store
from app.models.user import UserRole


def store_payload(name: str = "示例店铺") -> dict[str, str]:
    return {
        "store_name": name,
        "platform": "taobao",
        "external_store_id": "external-001",
        "owner_name": "运营甲",
        "remark": "Phase 2A",
    }


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_can_create_store(
    role: UserRole,
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/stores",
        json=store_payload(),
        headers=auth_headers_factory(role),
    )

    assert response.status_code == 201
    assert response.json()["store_name"] == "示例店铺"
    assert response.json()["platform"] == "taobao"


def test_viewer_cannot_create_store(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/stores",
        json=store_payload(),
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "role", [UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]
)
def test_all_roles_can_query_stores(
    role: UserRole,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    db_session.add(Store(store_name="可查看店铺", platform=Platform.JD))
    db_session.commit()

    response = client.get(
        "/api/v1/stores", headers=auth_headers_factory(role)
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["store_name"] == "可查看店铺"


def test_update_store_distinguishes_omitted_and_explicit_null(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = Store(
        store_name="修改前",
        platform=Platform.TMALL,
        owner_name="保留负责人",
        remark="需要清空",
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)

    response = client.patch(
        f"/api/v1/stores/{store.id}",
        json={"store_name": "修改后", "remark": None},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    assert response.json()["store_name"] == "修改后"
    assert response.json()["owner_name"] == "保留负责人"
    assert response.json()["remark"] is None


def test_store_required_field_rejects_explicit_null(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    store = Store(store_name="不能清空名称", platform=Platform.OTHER)
    db_session.add(store)
    db_session.commit()

    response = client.patch(
        f"/api/v1/stores/{store.id}",
        json={"store_name": None},
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 422


def test_query_missing_store_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.get(
        "/api/v1/stores/9999",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "store_not_found"


def test_store_list_supports_pagination(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    db_session.add_all(
        [Store(store_name=f"店铺{i}", platform=Platform.OTHER) for i in range(3)]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/stores?page=2&page_size=1",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert len(response.json()["items"]) == 1
