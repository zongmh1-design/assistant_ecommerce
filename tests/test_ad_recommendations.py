"""AdRecommendation generation, editing, final decision and history tests."""

import json
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.core.security import decode_access_token
from app.main import app
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset, GeneratedAssetType
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.product import Product, ProductStatus
from app.models.product_diagnosis import ProductDiagnosis
from app.models.promotion_link import PromotionLink, PromotionLinkClick, PromotionLinkStatus
from app.models.store import Platform, Store
from app.models.user import UserRole


VALID_OUTPUT = {
    "summary": "用小规模预算验证现有卖点表达，不承诺收益。",
    "objective": "验证目标用户对两类创意表达的反馈。",
    "audience_segments": [{
        "segment_name": "年轻家庭", "description": "关注易用性的家庭用户",
        "rationale": "来自商品目标人群资料",
    }],
    "budget_plan": {
        "total_budget": "1000.00", "currency": "CNY",
        "allocation": [{
            "channel_or_test": "素材对照测试", "amount": "1000.00",
            "rationale": "仅为人工审核的预算建议",
        }],
        "rationale": "先验证假设，不自动修改预算",
    },
    "creative_tests": [{
        "test_name": "主图卖点测试", "asset_reference": "asset_1_image_v1",
        "hypothesis": "两种表达可能带来不同反馈",
        "success_metric": "上线后以同口径真实点击和转化数据比较",
    }],
    "bid_strategy": {
        "strategy_name": "人工控制测试", "rationale": "缺少历史数据",
        "constraints": ["不得自动出价", "不超过人工确认预算"],
    },
    "risk_controls": [{
        "risk": "没有历史投放指标", "mitigation": "不预测 CTR、CVR 或 ROI",
    }],
    "next_steps": ["人工审核建议", "补充真实数据后复盘"],
}


class CapturingProvider:
    def __init__(self, output=None):
        self.output = output if output is not None else VALID_OUTPUT
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        return StructuredLLMResult(
            data=self.output,
            raw_output=json.dumps(self.output, ensure_ascii=False),
            source_type="mock_ai",
            provider_name="capturing",
            model_name="ad-test-model",
            usage={"total_tokens": 42},
        )


class FailingProvider:
    def generate_structured(self, **_):
        raise LLMProviderError("deterministic ad failure")


@pytest.fixture
def provider_override():
    def set_provider(provider):
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Ad Store {suffix}", platform=Platform.DOUYIN)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=f"Ad Product {suffix}",
        platform=Platform.DOUYIN,
        category="家居",
        price=Decimal("129.90"),
        target_audience="年轻家庭",
        selling_points=["轻量", "易清洁"],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_full_context(db: Session, product: Product) -> None:
    diagnosis = ProductDiagnosis(
        product_id=product.id, source_type="mock_ai", positioning="轻量家居用品",
        price_band="已知商品价位", audience_insights=["年轻家庭"],
        pain_points=["清洁耗时"], selling_point_analysis=["易清洁"],
        risks=["缺少真实经营数据"], recommendations=["小规模测试"],
        raw_output="{}", input_context_json={"product": {"name": product.name}},
    )
    db.add(diagnosis)
    for plan_type in (CreativePlanType.MAIN_IMAGE, CreativePlanType.VIDEO_SCRIPT):
        plan = CreativePlan(
            product_id=product.id, plan_type=plan_type,
            title=f"Selected {plan_type.value}", content_json={"known": "content"},
            rationale_text="test", status=CreativePlanStatus.SELECTED,
            input_context_json={"product": {"name": product.name}},
        )
        db.add(plan)
        db.flush()
        if plan_type == CreativePlanType.MAIN_IMAGE:
            job = GenerationJob(
                product_id=product.id, creative_plan_id=plan.id,
                job_kind=GenerationJobKind.IMAGE,
                job_status=GenerationJobStatus.SUCCEEDED, attempts=1,
                result_json={"asset_type": "image", "url": "mock://image.png", "width": 1024, "height": 1024},
            )
            db.add(job)
            db.flush()
            db.add(GeneratedAsset(
                product_id=product.id, creative_plan_id=plan.id,
                generation_job_id=job.id, asset_type=GeneratedAssetType.IMAGE,
                asset_url="mock://image.png", model_name="mock_image_generator",
                width=1024, height=1024, review_status=AssetReviewStatus.APPROVED,
                version_no=1, usage_scene="广告测试", score=88,
                tags_json=["主图", "年轻用户"],
            ))
    link = PromotionLink(
        product_id=product.id, link_name="社交链接",
        target_url="https://example.com/product", tracking_code="phase9context",
        utm_json={"utm_source": "douyin", "utm_medium": "social"},
        status=PromotionLinkStatus.ACTIVE, click_count=3, scene_text="短视频简介",
    )
    db.add(link)
    db.flush()
    db.add(PromotionLinkClick(
        promotion_link_id=link.id, client_ip="192.0.2.1", user_agent="secret-click-agent"
    ))
    db.commit()


def generate(client, product: Product, headers):
    return client.post(
        f"/api/v1/products/{product.id}/ad-recommendations/generate", headers=headers
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_generate_pending_historical_recommendation(
    client, db_session, auth_headers_factory, provider_override, role
):
    product = add_product(db_session)
    provider_override(CapturingProvider())
    response = generate(client, product, auth_headers_factory(role))
    assert response.status_code == 200
    body = response.json()
    assert body["confirm_status"] == "pending"
    assert body["confirmed_by"] is None and body["confirmed_at"] is None
    assert body["provider_name"] == "capturing" and body["model_name"] == "ad-test-model"
    stored = db_session.get(AdRecommendation, body["id"])
    assert stored.budget_plan_json["total_budget"] == "1000.00"
    assert stored.budget_plan_json["allocation"][0]["amount"] == "1000.00"


def test_generation_permissions_and_product_404(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    assert generate(client, product, auth_headers_factory(UserRole.VIEWER)).status_code == 403
    response = client.post(
        "/api/v1/products/999999/ad-recommendations/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 404


def test_full_context_is_whitelisted_and_excludes_click_details(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    add_full_context(db_session, product)
    provider = CapturingProvider()
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    prompt = provider.calls[0]["user_prompt"]
    context = json.loads(prompt.split("AD_RECOMMENDATION_INPUT_JSON:\n", 1)[1])
    assert set(context["product"]) == {"name", "platform", "category", "price", "target_audience", "selling_points"}
    assert set(context["latest_diagnosis"]) == {"positioning", "audience_insights", "pain_points", "selling_point_analysis", "risks", "recommendations"}
    assert len(context["selected_creative_plans"]) == 2
    assert context["approved_assets"][0]["asset_reference"] == "asset_1_image_v1"
    assert set(context["active_promotion_links"][0]) == {"link_name", "scene_text", "utm_json", "click_count"}
    assert "192.0.2.1" not in prompt and "secret-click-agent" not in prompt
    assert "tracking_code" not in prompt and "target_url" not in prompt


def test_no_assets_links_or_clicks_still_generates_without_claiming_metrics(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    response = generate(client, product, auth_headers_factory(UserRole.OPERATOR))
    assert response.status_code == 200
    body = response.json()
    assert body["input_context_json"]["approved_assets"] == []
    assert body["input_context_json"]["active_promotion_links"] == []
    assert "没有已审核素材" in body["summary_text"]
    assert "当前无 CTR、CVR 或 ROI 结论" in body["creative_tests_json"][0]["success_metric"]


def test_mock_output_is_deterministic_and_schema_valid(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = generate(client, product, headers)
    second = generate(client, product, headers)
    assert first.status_code == second.status_code == 200
    comparable = ["summary_text", "objective_text", "audience_segments_json", "budget_plan_json", "creative_tests_json", "bid_strategy_json", "risk_controls_json", "next_steps_json"]
    assert {key: first.json()[key] for key in comparable} == {key: second.json()[key] for key in comparable}
    assert db_session.scalar(select(func.count()).select_from(AdRecommendation)) == 2


@pytest.mark.parametrize("provider", [FailingProvider(), CapturingProvider({"summary": "incomplete"})])
def test_provider_or_schema_failure_does_not_persist(
    client, db_session, auth_headers_factory, provider_override, provider
):
    product = add_product(db_session)
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(AdRecommendation)) == 0


def test_budget_allocation_mismatch_is_invalid_and_not_persisted(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    invalid = json.loads(json.dumps(VALID_OUTPUT))
    invalid["budget_plan"]["allocation"][0]["amount"] = "999.99"
    provider_override(CapturingProvider(invalid))
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_llm_output"
    assert db_session.scalar(select(func.count()).select_from(AdRecommendation)) == 0


def test_each_generate_appends_history_in_latest_first_order(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = generate(client, product, headers).json()
    second = generate(client, product, headers).json()
    listing = client.get(
        f"/api/v1/products/{product.id}/ad-recommendations", headers=headers
    ).json()
    assert listing["total"] == 2
    assert [item["id"] for item in listing["items"]] == [second["id"], first["id"]]


def test_operator_edits_pending_structured_content(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    recommendation = generate(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    response = client.patch(
        f"/api/v1/products/{product.id}/ad-recommendations/{recommendation['id']}",
        json={"summary_text": "人工修订摘要", "next_steps_json": ["人工确认下一步"]},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 200
    assert response.json()["summary_text"] == "人工修订摘要"
    assert response.json()["next_steps_json"] == ["人工确认下一步"]


def test_viewer_cannot_edit_or_confirm(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    recommendation = generate(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    base = f"/api/v1/products/{product.id}/ad-recommendations/{recommendation['id']}"
    assert client.patch(base, json={"summary_text": "no"}, headers=viewer).status_code == 403
    assert client.patch(base + "/confirmation", json={"confirm_status": "confirmed"}, headers=viewer).status_code == 403


@pytest.mark.parametrize("status", ["confirmed", "rejected"])
def test_human_decision_sets_current_user_time_remark_and_freezes_body(
    client, db_session, auth_headers_factory, status
):
    product = add_product(db_session)
    recommendation = generate(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    operator_headers = auth_headers_factory(UserRole.OPERATOR)
    expected_user_id = decode_access_token(operator_headers["Authorization"].split(" ", 1)[1])["user_id"]
    path = f"/api/v1/products/{product.id}/ad-recommendations/{recommendation['id']}"
    response = client.patch(
        path + "/confirmation",
        json={"confirm_status": status, "confirm_remark": f"人工{status}"},
        headers=operator_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confirm_status"] == status
    assert body["confirmed_by"] == expected_user_id
    assert body["confirmed_at"] is not None
    datetime.fromisoformat(body["confirmed_at"])
    assert body["confirm_remark"] == f"人工{status}"
    assert client.patch(
        path, json={"summary_text": "终态后禁止修改"}, headers=operator_headers
    ).status_code == 409
    assert client.patch(
        path + "/confirmation", json={"confirm_status": "confirmed"}, headers=operator_headers
    ).status_code == 409


def test_confirmation_rejects_pending_and_spoofed_confirmer_fields(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    recommendation = generate(client, product, headers).json()
    path = f"/api/v1/products/{product.id}/ad-recommendations/{recommendation['id']}/confirmation"
    assert client.patch(path, json={"confirm_status": "pending"}, headers=headers).status_code == 422
    assert client.patch(
        path, json={"confirm_status": "confirmed", "confirmed_by": 999}, headers=headers
    ).status_code == 422


def test_product_recommendation_mismatch_and_protected_edit_fields(
    client, db_session, auth_headers_factory
):
    first = add_product(db_session, "a")
    second = add_product(db_session, "b")
    headers = auth_headers_factory(UserRole.ADMIN)
    recommendation = generate(client, first, headers).json()
    mismatch = client.patch(
        f"/api/v1/products/{second.id}/ad-recommendations/{recommendation['id']}",
        json={"summary_text": "wrong product"}, headers=headers,
    )
    assert mismatch.status_code == 404
    for field, value in (("product_id", second.id), ("provider_name", "fake"), ("confirmed_by", 1), ("input_context_json", {})):
        response = client.patch(
            f"/api/v1/products/{first.id}/ad-recommendations/{recommendation['id']}",
            json={field: value}, headers=headers,
        )
        assert response.status_code == 422


def test_query_filter_pagination_detail_and_viewer_access(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    admin = auth_headers_factory(UserRole.ADMIN)
    first = generate(client, product, admin).json()
    second = generate(client, product, admin).json()
    client.patch(
        f"/api/v1/products/{product.id}/ad-recommendations/{first['id']}/confirmation",
        json={"confirm_status": "confirmed"}, headers=admin,
    )
    viewer = auth_headers_factory(UserRole.VIEWER)
    listing = client.get(
        f"/api/v1/products/{product.id}/ad-recommendations?confirm_status=pending&page=1&page_size=1",
        headers=viewer,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1 and listing.json()["items"][0]["id"] == second["id"]
    detail = client.get(
        f"/api/v1/products/{product.id}/ad-recommendations/{first['id']}", headers=viewer
    )
    assert detail.status_code == 200 and detail.json()["confirm_status"] == "confirmed"


def test_confirmation_commit_failure_rolls_back_all_decision_fields(
    client, db_session, auth_headers_factory, monkeypatch
):
    product = add_product(db_session)
    recommendation = generate(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    from app.schemas.ad_recommendation import AdRecommendationConfirmation
    from app.services.ad_recommendation_service import AdRecommendationService

    service = AdRecommendationService(db_session)
    original_commit = db_session.commit
    monkeypatch.setattr(db_session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
    with pytest.raises(RuntimeError):
        service.confirm(
            product.id, recommendation["id"],
            AdRecommendationConfirmation(confirm_status="confirmed", confirm_remark="should rollback"),
            current_user_id=1,
        )
    monkeypatch.setattr(db_session, "commit", original_commit)
    db_session.expire_all()
    stored = db_session.get(AdRecommendation, recommendation["id"])
    assert stored.confirm_status == AdRecommendationConfirmStatus.PENDING
    assert stored.confirmed_by is None and stored.confirmed_at is None and stored.confirm_remark is None
