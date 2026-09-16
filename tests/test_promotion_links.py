"""Promotion-link suggestion, CRUD, redirect, privacy and transaction tests."""

import json
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.main import app
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset, GeneratedAssetType
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.product import Product, ProductStatus
from app.models.promotion_link import PromotionLink, PromotionLinkClick, PromotionLinkStatus
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.repositories.promotion_link_repository import PromotionLinkRepository
from app.schemas.promotion_link import PromotionLinkCreate
from app.services.promotion_link_service import PromotionLinkService


VALID_SUGGESTION = {
    "link_name": "新品社交分享",
    "scene_text": "社交媒体",
    "utm_source": "xiaohongshu",
    "utm_medium": "social",
    "utm_campaign": "summer_launch",
    "utm_content": "main_image_v1",
    "rationale": "参数与已知分享场景一致。",
}


class CapturingProvider:
    def __init__(self, output=None):
        self.output = output if output is not None else VALID_SUGGESTION
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        return StructuredLLMResult(
            data=self.output,
            raw_output=json.dumps(self.output, ensure_ascii=False),
            source_type="mock_ai",
        )


class FailingProvider:
    def generate_structured(self, **_):
        raise LLMProviderError("deterministic provider failure")


@pytest.fixture
def provider_override():
    def set_provider(provider):
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Promotion Store {suffix}", platform=Platform.TAOBAO)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=f"Promotion Product {suffix}",
        platform=Platform.TAOBAO,
        category="家居",
        price=Decimal("99.00"),
        target_audience="年轻家庭",
        selling_points=["轻量", "易清洁"],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_selected_plan_and_asset(db: Session, product: Product):
    plan = CreativePlan(
        product_id=product.id,
        plan_type=CreativePlanType.MAIN_IMAGE,
        title="场景主图",
        content_json={"core_copy": ["轻量易清洁"]},
        rationale_text="突出场景",
        status=CreativePlanStatus.SELECTED,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(plan)
    db.flush()
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.SUCCEEDED,
        attempts=1,
        result_json={"asset_type": "image", "url": "mock://image.png", "width": 1024, "height": 1024},
    )
    db.add(job)
    db.flush()
    asset = GeneratedAsset(
        product_id=product.id,
        creative_plan_id=plan.id,
        generation_job_id=job.id,
        asset_type=GeneratedAssetType.IMAGE,
        asset_url="mock://image.png",
        model_name="mock_image_generator",
        width=1024,
        height=1024,
        review_status=AssetReviewStatus.APPROVED,
        version_no=1,
        usage_scene="商品详情页",
        tags_json=["主图", "年轻用户"],
    )
    db.add(asset)
    db.commit()
    return plan, asset


def create_link(client, product: Product, headers, **overrides):
    payload = {
        "link_name": "社交分享链接",
        "target_url": "https://example.com/products/one",
        "utm_json": {"utm_source": "xiaohongshu", "utm_medium": "social"},
        "scene_text": "社交媒体",
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/products/{product.id}/promotion-links", json=payload, headers=headers
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_generate_strict_suggestion(
    client, db_session, auth_headers_factory, provider_override, role
):
    product = add_product(db_session)
    provider = CapturingProvider()
    provider_override(provider)
    response = client.post(
        f"/api/v1/products/{product.id}/promotion-links/generate",
        headers=auth_headers_factory(role),
    )
    assert response.status_code == 200
    assert response.json() == VALID_SUGGESTION
    assert provider.calls[0]["response_schema"].__name__ == "PromotionLinkSuggestion"
    assert "tracking_code" not in response.json()
    assert "target_url" not in response.json()


def test_suggestion_context_is_whitelisted_and_uses_selected_plan_and_approved_asset(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    add_selected_plan_and_asset(db_session, product)
    provider = CapturingProvider()
    provider_override(provider)
    response = client.post(
        f"/api/v1/products/{product.id}/promotion-links/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 200
    prompt = provider.calls[0]["user_prompt"]
    context = json.loads(prompt.split("PROMOTION_LINK_INPUT_JSON:\n", 1)[1])
    assert set(context["product"]) == {"name", "platform", "category", "target_audience", "selling_points"}
    assert set(context["selected_creative_plan"]) == {"plan_type", "title", "content_json"}
    assert set(context["approved_asset"]) == {"asset_type", "usage_scene", "tags_json"}
    assert "id" not in prompt and "api_key" not in prompt.lower()


def test_suggestion_permissions_missing_product_and_provider_failures(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    viewer = client.post(
        f"/api/v1/products/{product.id}/promotion-links/generate",
        headers=auth_headers_factory(UserRole.VIEWER),
    )
    assert viewer.status_code == 403
    missing = client.post(
        "/api/v1/products/999999/promotion-links/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert missing.status_code == 404
    provider_override(FailingProvider())
    failed = client.post(
        f"/api/v1/products/{product.id}/promotion-links/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "llm_provider_error"


def test_invalid_suggestion_schema_returns_stable_error(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    provider_override(CapturingProvider({"link_name": "missing fields"}))
    response = client.post(
        f"/api/v1/products/{product.id}/promotion-links/generate",
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_llm_output"


def test_mock_suggestion_is_deterministic_and_schema_valid(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = client.post(f"/api/v1/products/{product.id}/promotion-links/generate", headers=headers)
    second = client.post(f"/api/v1/products/{product.id}/promotion-links/generate", headers=headers)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert "tracking_code" not in first.json() and "target_url" not in first.json()
    assert db_session.scalar(select(func.count()).select_from(PromotionLink)) == 0


def test_create_generates_unique_code_and_server_defaults(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    first = create_link(client, product, headers)
    second = create_link(client, product, headers, link_name="第二条")
    assert first.status_code == second.status_code == 201
    assert first.json()["tracking_code"] != second.json()["tracking_code"]
    assert first.json()["tracking_code"].replace("-", "").replace("_", "").isalnum()
    assert first.json()["click_count"] == 0
    assert first.json()["status"] == "active"


def test_tracking_code_collision_is_checked_and_regenerated(
    db_session, monkeypatch
):
    product = add_product(db_session)
    service = PromotionLinkService(db_session)
    first = service.create(
        product.id,
        PromotionLinkCreate(link_name="first", target_url="https://example.com/first"),
    )
    generated = iter([first.tracking_code, "new_url_safe_code"])
    monkeypatch.setattr(
        "app.services.promotion_link_service.secrets.token_urlsafe",
        lambda _: next(generated),
    )
    second = service.create(
        product.id,
        PromotionLinkCreate(link_name="second", target_url="https://example.com/second"),
    )
    assert second.tracking_code == "new_url_safe_code"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "data:text/plain,test", "ftp://example.com/file"])
def test_create_rejects_unsafe_target_url(client, db_session, auth_headers_factory, url):
    product = add_product(db_session)
    response = create_link(client, product, auth_headers_factory(UserRole.ADMIN), target_url=url)
    assert response.status_code == 422


def test_utm_json_rejects_unapproved_fields(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    response = create_link(
        client,
        product,
        auth_headers_factory(UserRole.ADMIN),
        utm_json={"utm_source": "social", "arbitrary_tracking": "forbidden"},
    )
    assert response.status_code == 422


def test_viewer_cannot_create_or_update_but_can_query(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    admin = auth_headers_factory(UserRole.ADMIN)
    link = create_link(client, product, admin).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert create_link(client, product, viewer).status_code == 403
    assert client.get(f"/api/v1/products/{product.id}/promotion-links", headers=viewer).status_code == 200
    assert client.patch(
        f"/api/v1/products/{product.id}/promotion-links/{link['id']}",
        json={"status": "inactive"}, headers=viewer,
    ).status_code == 403


def test_query_filter_pagination_detail_and_product_mismatch(
    client, db_session, auth_headers_factory
):
    first_product = add_product(db_session, "a")
    second_product = add_product(db_session, "b")
    headers = auth_headers_factory(UserRole.ADMIN)
    first = create_link(client, first_product, headers).json()
    second = create_link(client, first_product, headers, link_name="inactive").json()
    client.patch(
        f"/api/v1/products/{first_product.id}/promotion-links/{second['id']}",
        json={"status": "inactive"}, headers=headers,
    )
    listing = client.get(
        f"/api/v1/products/{first_product.id}/promotion-links?status=active&page=1&page_size=1",
        headers=headers,
    ).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == first["id"]
    assert client.get(
        f"/api/v1/products/{first_product.id}/promotion-links/{first['id']}", headers=headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/products/{second_product.id}/promotion-links/{first['id']}", headers=headers
    ).status_code == 404


def test_update_keeps_tracking_code_and_rejects_protected_fields(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    link = create_link(client, product, headers).json()
    changed = client.patch(
        f"/api/v1/products/{product.id}/promotion-links/{link['id']}",
        json={"target_url": "https://example.org/new", "scene_text": None, "status": "inactive"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json()["tracking_code"] == link["tracking_code"]
    assert changed.json()["status"] == "inactive"
    for field, value in (("tracking_code", "client-code"), ("click_count", 99), ("product_id", 99)):
        response = client.patch(
            f"/api/v1/products/{product.id}/promotion-links/{link['id']}",
            json={field: value}, headers=headers,
        )
        assert response.status_code == 422


def test_public_redirect_records_click_and_atomic_count(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    link = create_link(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    response = client.get(
        f"/api/v1/r/{link['tracking_code']}",
        headers={"user-agent": "phase8-test-agent"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == link["target_url"]
    db_session.expire_all()
    stored = db_session.get(PromotionLink, link["id"])
    click = db_session.scalar(select(PromotionLinkClick).where(PromotionLinkClick.promotion_link_id == link["id"]))
    assert stored.click_count == 1
    assert click.user_agent == "phase8-test-agent"
    assert click.client_ip is not None


def test_redirect_missing_or_inactive_does_not_record_click(
    client, db_session, auth_headers_factory
):
    assert client.get("/api/v1/r/does-not-exist", follow_redirects=False).status_code == 404
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    link = create_link(client, product, headers).json()
    client.patch(
        f"/api/v1/products/{product.id}/promotion-links/{link['id']}",
        json={"status": "inactive"}, headers=headers,
    )
    response = client.get(f"/api/v1/r/{link['tracking_code']}", follow_redirects=False)
    assert response.status_code == 410
    assert db_session.scalar(select(func.count()).select_from(PromotionLinkClick)) == 0


def test_target_update_keeps_old_code_and_redirects_to_new_target(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    link = create_link(client, product, headers).json()
    client.patch(
        f"/api/v1/products/{product.id}/promotion-links/{link['id']}",
        json={"target_url": "https://example.org/replaced"}, headers=headers,
    )
    response = client.get(f"/api/v1/r/{link['tracking_code']}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.org/replaced"


def test_click_list_is_authenticated_readable_and_paginated(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    link = create_link(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    for marker in ("one", "two"):
        client.get(f"/api/v1/r/{link['tracking_code']}", headers={"user-agent": marker}, follow_redirects=False)
    path = f"/api/v1/products/{product.id}/promotion-links/{link['id']}/clicks?page=1&page_size=1"
    assert client.get(path).status_code == 401
    response = client.get(path, headers=auth_headers_factory(UserRole.VIEWER))
    assert response.status_code == 200
    assert response.json()["total"] == 2 and len(response.json()["items"]) == 1


def test_client_ip_and_user_agent_may_be_null(db_session):
    product = add_product(db_session)
    service = PromotionLinkService(db_session)
    link = service.create(product.id, PromotionLinkCreate(
        link_name="private", target_url="https://example.com", scene_text=None
    ))
    service.record_click(link.tracking_code, client_ip=None, user_agent=None)
    click = db_session.scalar(select(PromotionLinkClick).where(PromotionLinkClick.promotion_link_id == link.id))
    assert click.client_ip is None and click.user_agent is None


def test_click_insert_failure_rolls_back_counter(db_session, monkeypatch):
    product = add_product(db_session)
    service = PromotionLinkService(db_session)
    link = service.create(product.id, PromotionLinkCreate(link_name="tx", target_url="https://example.com"))
    monkeypatch.setattr(service.clicks, "add", lambda _: (_ for _ in ()).throw(RuntimeError("insert failed")))
    with pytest.raises(RuntimeError):
        service.record_click(link.tracking_code, client_ip=None, user_agent=None)
    db_session.expire_all()
    assert db_session.get(PromotionLink, link.id).click_count == 0
    assert db_session.scalar(select(func.count()).select_from(PromotionLinkClick)) == 0


def test_counter_failure_rolls_back_click(db_session, monkeypatch):
    product = add_product(db_session)
    service = PromotionLinkService(db_session)
    link = service.create(product.id, PromotionLinkCreate(link_name="tx", target_url="https://example.com"))
    monkeypatch.setattr(service.links, "increment_click_count_atomic", lambda _: False)
    with pytest.raises(Exception):
        service.record_click(link.tracking_code, client_ip=None, user_agent=None)
    db_session.expire_all()
    assert db_session.get(PromotionLink, link.id).click_count == 0
    assert db_session.scalar(select(func.count()).select_from(PromotionLinkClick)) == 0


def test_repository_counter_uses_atomic_update_expression():
    captured = []

    class Result:
        rowcount = 1

    class FakeSession:
        def execute(self, statement):
            captured.append(statement)
            return Result()

    assert PromotionLinkRepository(FakeSession()).increment_click_count_atomic(7)
    sql = str(captured[0].compile(compile_kwargs={"literal_binds": True}))
    assert "click_count=(promotion_links.click_count + 1)" in sql
    assert "promotion_links.status = 'active'" in sql
