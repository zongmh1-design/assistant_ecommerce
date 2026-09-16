"""AdExperiment generation, binding, editing, state and query tests."""

import json
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.main import app
from app.models.ad_experiment import AdExperiment, AdExperimentStatus
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset, GeneratedAssetType
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.product import Product, ProductStatus
from app.models.promotion_link import PromotionLink, PromotionLinkStatus
from app.models.store import Platform, Store
from app.models.user import UserRole


VALID_OUTPUT = {
    "experiment_name": "核心卖点验证",
    "target_text": "验证目标用户对卖点表达的反馈",
    "audience_text": "年轻家庭",
    "budget_amount": "800.00",
    "success_metric_text": "上线后观察同口径点击率和落地页访问量，不预设历史指标",
    "hypothesis_text": "待验证假设：轻量卖点可能获得更积极反馈",
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
            model_name="experiment-test-model",
            usage={"total_tokens": 30},
        )


class FailingProvider:
    def generate_structured(self, **_):
        raise LLMProviderError("deterministic experiment failure")


@pytest.fixture
def provider_override():
    def set_provider(provider):
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Experiment Store {suffix}", platform=Platform.JD)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id, name=f"Experiment Product {suffix}",
        platform=Platform.JD, category="家居", price=Decimal("199.90"),
        target_audience="年轻家庭", selling_points=["轻量", "耐用"],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_recommendation(
    db: Session, product: Product,
    status: AdRecommendationConfirmStatus = AdRecommendationConfirmStatus.CONFIRMED,
) -> AdRecommendation:
    recommendation = AdRecommendation(
        product_id=product.id, summary_text="保守测试建议",
        objective_text="验证素材反馈",
        audience_segments_json=[{
            "segment_name": "年轻家庭", "description": "已知目标用户",
            "rationale": "来自商品资料",
        }],
        budget_plan_json={
            "total_budget": "800.00", "currency": "CNY",
            "allocation": [{
                "channel_or_test": "素材测试", "amount": "800.00",
                "rationale": "人工预算建议",
            }],
            "rationale": "小规模验证",
        },
        creative_tests_json=[{
            "test_name": "主图测试", "asset_reference": "asset_1_image_v1",
            "hypothesis": "表达差异可能影响反馈", "success_metric": "实际点击反馈",
        }],
        bid_strategy_json={
            "strategy_name": "人工控制", "rationale": "无历史数据",
            "constraints": ["不自动出价"],
        },
        risk_controls_json=[{"risk": "数据不足", "mitigation": "不预测收益"}],
        next_steps_json=["人工确认实验"], confirm_status=status,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def add_asset(
    db: Session, product: Product,
    status: AssetReviewStatus = AssetReviewStatus.APPROVED,
) -> GeneratedAsset:
    plan = CreativePlan(
        product_id=product.id, plan_type=CreativePlanType.MAIN_IMAGE,
        title="Experiment source", content_json={"known": "content"},
        rationale_text="fixture", status=CreativePlanStatus.SELECTED,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(plan)
    db.flush()
    job = GenerationJob(
        product_id=product.id, creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE, job_status=GenerationJobStatus.SUCCEEDED,
        attempts=1, result_json={
            "asset_type": "image", "url": "mock://experiment.png",
            "width": 1024, "height": 1024,
        },
    )
    db.add(job)
    db.flush()
    asset = GeneratedAsset(
        product_id=product.id, creative_plan_id=plan.id, generation_job_id=job.id,
        asset_type=GeneratedAssetType.IMAGE, asset_url="mock://experiment.png",
        model_name="mock_image_generator", width=1024, height=1024,
        review_status=status, version_no=1, usage_scene="广告测试",
        score=90, tags_json=["主图"],
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def add_link(
    db: Session, product: Product,
    status: PromotionLinkStatus = PromotionLinkStatus.ACTIVE,
) -> PromotionLink:
    link = PromotionLink(
        product_id=product.id, link_name="Experiment Link",
        target_url="https://example.com/product",
        tracking_code=f"experiment-{product.id}-{status.value}",
        utm_json={"utm_source": "jd", "utm_medium": "test"},
        status=status, click_count=2, scene_text="实验链接",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def generate(client, product, recommendation, headers, **relations):
    payload = {"recommendation_id": recommendation.id, **relations}
    return client.post(
        f"/api/v1/products/{product.id}/ad-experiments/generate",
        json=payload, headers=headers,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_confirmed_recommendation_generates_draft_with_decimal_and_metadata(
    client, db_session, auth_headers_factory, provider_override, role
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    provider_override(CapturingProvider())
    response = generate(client, product, recommendation, auth_headers_factory(role))
    assert response.status_code == 200
    body = response.json()
    assert body["ad_recommendation_id"] == recommendation.id
    assert body["experiment_status"] == "draft"
    assert body["budget_amount"] == "800.00"
    assert body["provider_name"] == "capturing"


@pytest.mark.parametrize(
    "status",
    [AdRecommendationConfirmStatus.PENDING, AdRecommendationConfirmStatus.REJECTED],
)
def test_pending_or_rejected_recommendation_cannot_generate(
    client, db_session, auth_headers_factory, status
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product, status)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ad_recommendation_not_confirmed"


def test_product_recommendation_mismatch_is_404(client, db_session, auth_headers_factory):
    first = add_product(db_session, "a")
    second = add_product(db_session, "b")
    recommendation = add_recommendation(db_session, first)
    response = generate(
        client, second, recommendation, auth_headers_factory(UserRole.ADMIN)
    )
    assert response.status_code == 404


def test_approved_asset_and_active_link_bind_and_context_is_whitelisted(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    asset = add_asset(db_session, product)
    link = add_link(db_session, product)
    provider = CapturingProvider()
    provider_override(provider)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.OPERATOR),
        related_asset_id=asset.id, related_link_id=link.id,
    )
    assert response.status_code == 200
    assert response.json()["related_asset_id"] == asset.id
    assert response.json()["related_link_id"] == link.id
    context = json.loads(
        provider.calls[0]["user_prompt"].split("AD_EXPERIMENT_INPUT_JSON:\n", 1)[1]
    )
    assert set(context["product"]) == {"name", "platform", "category", "price", "target_audience", "selling_points"}
    assert set(context["approved_asset"]) == {"asset_reference", "asset_type", "version_no", "usage_scene", "score", "tags_json"}
    assert set(context["active_promotion_link"]) == {"link_reference", "link_name", "scene_text", "utm_json", "click_count"}
    prompt = provider.calls[0]["user_prompt"]
    assert link.tracking_code not in prompt and link.target_url not in prompt


@pytest.mark.parametrize("status", [AssetReviewStatus.PENDING, AssetReviewStatus.REJECTED])
def test_unapproved_asset_cannot_bind(client, db_session, auth_headers_factory, status):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    asset = add_asset(db_session, product, status)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN),
        related_asset_id=asset.id,
    )
    assert response.status_code == 409


def test_inactive_link_cannot_bind(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    link = add_link(db_session, product, PromotionLinkStatus.INACTIVE)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN),
        related_link_id=link.id,
    )
    assert response.status_code == 409


def test_asset_and_link_from_other_product_are_404(client, db_session, auth_headers_factory):
    product = add_product(db_session, "a")
    other = add_product(db_session, "b")
    recommendation = add_recommendation(db_session, product)
    asset = add_asset(db_session, other)
    link = add_link(db_session, other)
    headers = auth_headers_factory(UserRole.ADMIN)
    assert generate(client, product, recommendation, headers, related_asset_id=asset.id).status_code == 404
    assert generate(client, product, recommendation, headers, related_link_id=link.id).status_code == 404


def test_optional_asset_and_link_may_be_absent_and_mock_does_not_invent_metrics(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["related_asset_id"] is None and body["related_link_id"] is None
    assert body["input_context_json"]["approved_asset"] is None
    assert "当前不预设 CTR、CVR 或 ROI 数值" in body["success_metric_text"]
    assert body["hypothesis_text"].startswith("待验证假设")


@pytest.mark.parametrize("provider", [FailingProvider(), CapturingProvider({"experiment_name": "incomplete"})])
def test_provider_or_invalid_schema_does_not_persist(
    client, db_session, auth_headers_factory, provider_override, provider
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    provider_override(provider)
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    )
    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(AdExperiment)) == 0


def test_nonpositive_budget_is_invalid_and_not_persisted(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    invalid = {**VALID_OUTPUT, "budget_amount": "0.00"}
    provider_override(CapturingProvider(invalid))
    response = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    )
    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(AdExperiment)) == 0


def test_operator_edits_draft_and_can_unbind_relations(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    asset = add_asset(db_session, product)
    link = add_link(db_session, product)
    experiment = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN),
        related_asset_id=asset.id, related_link_id=link.id,
    ).json()
    response = client.patch(
        f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}",
        json={
            "experiment_name": "人工修订实验", "budget_amount": "600.00",
            "related_asset_id": None, "related_link_id": None,
        },
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 200
    assert response.json()["experiment_name"] == "人工修订实验"
    assert response.json()["budget_amount"] == "600.00"
    assert response.json()["related_asset_id"] is None


def test_viewer_cannot_generate_edit_or_change_status(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    admin = auth_headers_factory(UserRole.ADMIN)
    experiment = generate(client, product, recommendation, admin).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert generate(client, product, recommendation, viewer).status_code == 403
    base = f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}"
    assert client.patch(base, json={"target_text": "no"}, headers=viewer).status_code == 403
    assert client.patch(base + "/status", json={"experiment_status": "confirmed"}, headers=viewer).status_code == 403


@pytest.mark.parametrize(
    "status",
    [AdExperimentStatus.CONFIRMED, AdExperimentStatus.RUNNING, AdExperimentStatus.FINISHED, AdExperimentStatus.CANCELLED],
)
def test_non_draft_content_is_frozen(client, db_session, auth_headers_factory, status):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    experiment = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    ).json()
    stored = db_session.get(AdExperiment, experiment["id"])
    stored.experiment_status = status
    db_session.commit()
    response = client.patch(
        f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}",
        json={"target_text": "forbidden"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 409


def test_edit_revalidates_asset_link_and_recommendation_id_is_protected(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    bad_asset = add_asset(db_session, product, AssetReviewStatus.PENDING)
    bad_link = add_link(db_session, product, PromotionLinkStatus.INACTIVE)
    headers = auth_headers_factory(UserRole.ADMIN)
    experiment = generate(client, product, recommendation, headers).json()
    base = f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}"
    assert client.patch(base, json={"related_asset_id": bad_asset.id}, headers=headers).status_code == 409
    assert client.patch(base, json={"related_link_id": bad_link.id}, headers=headers).status_code == 409
    assert client.patch(base, json={"ad_recommendation_id": 999}, headers=headers).status_code == 422


@pytest.mark.parametrize(
    ("start", "desired"),
    [
        (AdExperimentStatus.DRAFT, "confirmed"),
        (AdExperimentStatus.DRAFT, "cancelled"),
        (AdExperimentStatus.CONFIRMED, "running"),
        (AdExperimentStatus.CONFIRMED, "cancelled"),
        (AdExperimentStatus.RUNNING, "finished"),
        (AdExperimentStatus.RUNNING, "cancelled"),
    ],
)
def test_allowed_status_transitions(client, db_session, auth_headers_factory, start, desired):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    experiment = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    ).json()
    stored = db_session.get(AdExperiment, experiment["id"])
    stored.experiment_status = start
    db_session.commit()
    response = client.patch(
        f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}/status",
        json={"experiment_status": desired},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 200
    assert response.json()["experiment_status"] == desired


@pytest.mark.parametrize(
    ("start", "desired"),
    [
        (AdExperimentStatus.DRAFT, "running"),
        (AdExperimentStatus.DRAFT, "finished"),
        (AdExperimentStatus.CONFIRMED, "finished"),
        (AdExperimentStatus.RUNNING, "draft"),
        (AdExperimentStatus.FINISHED, "running"),
        (AdExperimentStatus.CANCELLED, "running"),
    ],
)
def test_forbidden_status_transitions(client, db_session, auth_headers_factory, start, desired):
    product = add_product(db_session)
    recommendation = add_recommendation(db_session, product)
    experiment = generate(
        client, product, recommendation, auth_headers_factory(UserRole.ADMIN)
    ).json()
    stored = db_session.get(AdExperiment, experiment["id"])
    stored.experiment_status = start
    db_session.commit()
    response = client.patch(
        f"/api/v1/products/{product.id}/ad-experiments/{experiment['id']}/status",
        json={"experiment_status": desired},
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 409


def test_query_filters_pagination_detail_and_product_mismatch(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session, "a")
    other = add_product(db_session, "b")
    first_rec = add_recommendation(db_session, product)
    second_rec = add_recommendation(db_session, product)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = generate(client, product, first_rec, headers).json()
    second = generate(client, product, second_rec, headers).json()
    client.patch(
        f"/api/v1/products/{product.id}/ad-experiments/{first['id']}/status",
        json={"experiment_status": "confirmed"}, headers=headers,
    )
    viewer = auth_headers_factory(UserRole.VIEWER)
    listing = client.get(
        f"/api/v1/products/{product.id}/ad-experiments?experiment_status=draft&ad_recommendation_id={second_rec.id}&page=1&page_size=1",
        headers=viewer,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == second["id"]
    assert client.get(
        f"/api/v1/products/{product.id}/ad-experiments/{first['id']}", headers=viewer
    ).status_code == 200
    assert client.get(
        f"/api/v1/products/{other.id}/ad-experiments/{first['id']}", headers=viewer
    ).status_code == 404
