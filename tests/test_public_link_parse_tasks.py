"""Public-link parse task success, failure, confirmation and rollback tests."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.competitors import get_public_link_parser
from app.integrations.mock_public_link_parser import MockPublicLinkParser
from app.integrations.public_link_parser import PublicLinkParseResult
from app.main import app
from app.models.competitor import Competitor, PublicLinkParseTask, PublicLinkParseTaskStatus
from app.models.product import Product, ProductStatus
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.repositories.competitor_repository import CompetitorRepository
from app.schemas.competitor import PublicLinkParseTaskCreate
from app.services.public_link_parse_service import PublicLinkParseService


def add_product(db: Session) -> Product:
    store = Store(store_name="解析任务店铺", platform=Platform.OTHER)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name="解析任务商品",
        platform=Platform.OTHER,
        price=Decimal("39.90"),
        selling_points=[],
        images_json=[],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_task(
    client: TestClient,
    product_id: int,
    headers: dict[str, str],
    source_url: str = "https://example.com/products/phone-case-001",
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/products/{product_id}/competitors/import-url-tasks",
        json={"source_url": source_url},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_task_is_pending_and_does_not_create_competitor(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    task = create_task(
        client, product.id, auth_headers_factory(UserRole.OPERATOR)
    )

    assert task["task_status"] == "pending"
    assert task["attempts"] == 0
    assert task["result_json"] is None
    assert db_session.scalar(select(func.count()).select_from(Competitor)) == 0


def test_missing_product_cannot_create_task(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = client.post(
        "/api/v1/products/9999/competitors/import-url-tasks",
        json={"source_url": "https://example.com/products/phone-case-001"},
        headers=auth_headers_factory(UserRole.ADMIN),
    )

    assert response.status_code == 404


def test_successful_run_persists_running_transition_result_and_attempt(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    task = create_task(client, product.id, headers)
    observed: list[tuple[PublicLinkParseTaskStatus, int]] = []

    class ObservingParser:
        def parse(self, _: str) -> PublicLinkParseResult:
            db_session.expire_all()
            current = db_session.get(PublicLinkParseTask, task["id"])
            observed.append((current.task_status, current.attempts))
            return MockPublicLinkParser().parse(
                "https://example.com/products/phone-case-001"
            )

    app.dependency_overrides[get_public_link_parser] = lambda: ObservingParser()
    response = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/run",
        headers=headers,
    )
    app.dependency_overrides.pop(get_public_link_parser, None)

    assert response.status_code == 200
    assert observed == [(PublicLinkParseTaskStatus.RUNNING, 1)]
    body = response.json()
    assert body["task_status"] == "succeeded"
    assert body["attempts"] == 1
    assert body["error_message"] is None
    assert body["result_json"]["data_source"] == "mock_demo"
    assert body["result_json"]["name"] == "轻薄磁吸手机壳（Mock 演示）"
    assert Decimal(body["result_json"]["price"]) == Decimal("59.90")


def test_fixed_failure_url_marks_task_failed_with_clear_error(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    task = create_task(client, product.id, headers, "https://example.com/fail")

    response = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/run",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["task_status"] == "failed"
    assert response.json()["attempts"] == 1
    assert response.json()["result_json"] is None
    assert "configured test URL" in response.json()["error_message"]


def test_viewer_cannot_run_but_can_query_task(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    task = create_task(
        client, product.id, auth_headers_factory(UserRole.OPERATOR)
    )
    viewer = auth_headers_factory(UserRole.VIEWER)

    assert client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/run",
        headers=viewer,
    ).status_code == 403
    response = client.get(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}",
        headers=viewer,
    )
    assert response.status_code == 200
    assert response.json()["task_status"] == "pending"


def test_succeeded_task_confirmation_creates_one_competitor(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    task = create_task(client, product.id, headers)
    run = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/run",
        headers=headers,
    )
    assert run.status_code == 200

    confirmed = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/confirm",
        headers=headers,
    )

    assert confirmed.status_code == 201
    assert confirmed.json()["product_id"] == product.id
    assert confirmed.json()["name"] == "轻薄磁吸手机壳（Mock 演示）"
    db_session.expire_all()
    saved_task = db_session.get(PublicLinkParseTask, task["id"])
    assert saved_task.confirmed_competitor_id == confirmed.json()["id"]

    duplicate = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/confirm",
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Competitor)) == 1


def test_failed_task_cannot_be_confirmed(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    task = create_task(client, product.id, headers, "https://example.com/fail")
    client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/run",
        headers=headers,
    )

    response = client.post(
        f"/api/v1/products/{product.id}/link-parse-tasks/{task['id']}/confirm",
        headers=headers,
    )

    assert response.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Competitor)) == 0


def test_confirmation_rolls_back_competitor_and_task_together(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = add_product(db_session)
    parser = MockPublicLinkParser()
    service = PublicLinkParseService(db_session, parser)
    task = service.create_task(
        product.id,
        PublicLinkParseTaskCreate(
            source_url="https://example.com/products/phone-case-001"
        ),
    )
    task = service.run_task(product.id, task.id)
    original_add = CompetitorRepository.add

    def fail_after_add(
        repository: CompetitorRepository, competitor: Competitor
    ) -> Competitor:
        original_add(repository, competitor)
        raise RuntimeError("simulated confirmation failure")

    monkeypatch.setattr(CompetitorRepository, "add", fail_after_add)
    with pytest.raises(RuntimeError, match="simulated confirmation failure"):
        service.confirm(product.id, task.id)

    db_session.expire_all()
    saved_task = db_session.get(PublicLinkParseTask, task.id)
    assert saved_task.confirmed_competitor_id is None
    assert db_session.scalar(select(func.count()).select_from(Competitor)) == 0
