"""Review aggregation, structured AI generation, editing and history tests."""

import json
from datetime import datetime, timezone
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
from app.models.performance_record import PerformanceRecord
from app.models.product import Product, ProductStatus
from app.models.promotion_link import PromotionLink, PromotionLinkStatus
from app.models.review_report import ReviewReport
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.services.performance_record_service import PerformanceRecordService


VALID_OUTPUT = {
    "summary": "当前周期经营数据已由系统汇总。",
    "insights": [{
        "title": "流量表现", "finding": "点击来自已录入数据",
        "evidence": "total_clicks=110; overall_ctr=0.010891",
    }],
    "problem_judgements": [{
        "problem": "缺少外部基准", "evidence": "仅有当前周期数据", "severity": "medium",
    }],
    "next_actions": [{
        "action": "人工复核实验", "rationale": "继续验证假设", "priority": "high",
    }],
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
            model_name="review-test-model",
            usage={"total_tokens": 42},
        )


class FailingProvider:
    def __init__(self):
        self.calls = 0

    def generate_structured(self, **_):
        self.calls += 1
        raise LLMProviderError("deterministic review failure")


@pytest.fixture
def provider_override():
    def set_provider(provider):
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Review Store {suffix}", platform=Platform.JD)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id, name=f"Review Product {suffix}", platform=Platform.JD,
        category="家居", price=Decimal("199.90"), target_audience="年轻家庭",
        selling_points=["轻量", "耐用"], status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_experiment(db: Session, product: Product) -> AdExperiment:
    recommendation = AdRecommendation(
        product_id=product.id, summary_text="已确认建议", objective_text="验证表现",
        audience_segments_json=[], budget_plan_json={}, creative_tests_json=[],
        bid_strategy_json={}, risk_controls_json=[], next_steps_json=[],
        confirm_status=AdRecommendationConfirmStatus.CONFIRMED,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(recommendation)
    db.flush()
    experiment = AdExperiment(
        product_id=product.id, ad_recommendation_id=recommendation.id,
        experiment_name="轻量卖点实验", target_text="观察真实反馈",
        audience_text="年轻家庭", budget_amount=Decimal("200.00"),
        success_metric_text="观察同口径点击和转化", hypothesis_text="轻量表达可能改善反馈",
        experiment_status=AdExperimentStatus.FINISHED,
        input_context_json={"source": "fixture"},
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def add_asset(db: Session, product: Product) -> GeneratedAsset:
    plan = CreativePlan(
        product_id=product.id, plan_type=CreativePlanType.MAIN_IMAGE,
        title="轻量主图", content_json={"core_copy": "轻量"}, rationale_text="fixture",
        status=CreativePlanStatus.SELECTED, input_context_json={"source": "fixture"},
    )
    db.add(plan)
    db.flush()
    job = GenerationJob(
        product_id=product.id, creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE, job_status=GenerationJobStatus.SUCCEEDED,
        attempts=1, result_json={"asset_type": "image", "url": "mock://review.png", "width": 1024, "height": 1024},
    )
    db.add(job)
    db.flush()
    asset = GeneratedAsset(
        product_id=product.id, creative_plan_id=plan.id, generation_job_id=job.id,
        asset_type=GeneratedAssetType.IMAGE, asset_url="mock://review.png",
        model_name="mock_image_generator", width=1024, height=1024,
        review_status=AssetReviewStatus.APPROVED, version_no=1,
        usage_scene="广告测试", score=88, tags_json=["主图", "轻量"],
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def add_link(db: Session, product: Product) -> PromotionLink:
    link = PromotionLink(
        product_id=product.id, link_name="社交分享", target_url="https://example.com/product",
        tracking_code=f"review-{product.id}", utm_json={"utm_source": "social"},
        status=PromotionLinkStatus.ACTIVE, click_count=999, scene_text="社交媒体",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def add_record(
    db: Session, product: Product, *, start="2026-09-01T00:00:00+00:00",
    end="2026-09-02T00:00:00+00:00", impressions=100, clicks=10,
    conversions=2, spend="10.00", revenue="15.00", experiment=None,
    asset=None, link=None,
) -> PerformanceRecord:
    spend_decimal = Decimal(spend)
    revenue_decimal = Decimal(revenue)
    metrics = PerformanceRecordService.calculate_metrics(
        impressions, clicks, conversions, spend_decimal, revenue_decimal
    )
    record = PerformanceRecord(
        product_id=product.id,
        experiment_id=experiment.id if experiment else None,
        generated_asset_id=asset.id if asset else None,
        promotion_link_id=link.id if link else None,
        period_start=datetime.fromisoformat(start), period_end=datetime.fromisoformat(end),
        impressions=impressions, clicks=clicks, conversions=conversions,
        spend=spend_decimal, revenue=revenue_decimal,
        ctr=metrics.ctr, conversion_rate=metrics.conversion_rate, roi=metrics.roi,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def generate(client, product, headers, start="2026-09-01T00:00:00+00:00", end="2026-09-05T00:00:00+00:00"):
    return client.post(
        f"/api/v1/products/{product.id}/review-reports/generate",
        json={"period_start": start, "period_end": end}, headers=headers,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_generate_historical_report(
    client, db_session, auth_headers_factory, provider_override, role
):
    product = add_product(db_session)
    add_record(db_session, product)
    provider = CapturingProvider()
    provider_override(provider)
    first = generate(client, product, auth_headers_factory(role))
    second = generate(client, product, auth_headers_factory(role))
    assert first.status_code == second.status_code == 200
    assert first.json()["provider_name"] == "capturing"
    assert first.json()["model_name"] == "review-test-model"
    assert db_session.scalar(select(func.count()).select_from(ReviewReport)) == 2


def test_aggregation_recalculates_weighted_ratios_and_decimal_context(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    experiment = add_experiment(db_session, product)
    asset = add_asset(db_session, product)
    link = add_link(db_session, product)
    add_record(db_session, product, impressions=100, clicks=10, conversions=5,
               spend="100.00", revenue="150.00", experiment=experiment, asset=asset, link=link)
    add_record(db_session, product, start="2026-09-02T00:00:00+00:00",
               end="2026-09-03T00:00:00+00:00", impressions=10000, clicks=100,
               conversions=10, spend="300.00", revenue="500.00",
               experiment=experiment, asset=asset, link=link)
    provider = CapturingProvider()
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    context = json.loads(provider.calls[0]["user_prompt"].split("REVIEW_REPORT_INPUT_JSON:\n", 1)[1])
    totals = context["aggregated_performance"]
    assert totals == {
        "total_impressions": 10100, "total_clicks": 110, "total_conversions": 15,
        "total_spend": "400.00", "total_revenue": "650.00",
        "overall_ctr": "0.010891", "overall_conversion_rate": "0.136364",
        "overall_roi": "0.625000",
    }
    assert totals["overall_ctr"] != "0.055000"
    assert len(context["experiment_summaries"]) == 1
    assert len(context["asset_summaries"]) == 1
    assert len(context["promotion_link_summaries"]) == 1
    serialized = json.dumps(context, ensure_ascii=False)
    for forbidden_value in (asset.asset_url, link.tracking_code, link.target_url):
        assert forbidden_value not in serialized
    forbidden_keys = {
        "id", "experiment_id", "generated_asset_id", "promotion_link_id",
        "tracking_code", "target_url", "client_ip", "user_agent",
    }

    def collect_keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value), set())
        return set()

    assert collect_keys(context).isdisjoint(forbidden_keys)


def test_zero_spend_produces_null_overall_roi(client, db_session, auth_headers_factory, provider_override):
    product = add_product(db_session)
    add_record(db_session, product, spend="0.00", revenue="20.00")
    provider = CapturingProvider()
    provider_override(provider)
    assert generate(client, product, auth_headers_factory(UserRole.ADMIN)).status_code == 200
    context = json.loads(provider.calls[0]["user_prompt"].split("REVIEW_REPORT_INPUT_JSON:\n", 1)[1])
    assert context["aggregated_performance"]["overall_roi"] is None
    assert context["experiment_summaries"] == []
    assert context["asset_summaries"] == []
    assert context["promotion_link_summaries"] == []


def test_default_mock_provider_references_aggregated_metrics(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    add_record(db_session, product, impressions=100, clicks=10, conversions=2)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    body = response.json()
    assert body["provider_name"] == "mock"
    assert body["model_name"] == "mock-review-report"
    assert "total_clicks=10" in body["insights_json"][0]["evidence"]
    assert "overall_ctr=0.100000" in body["insights_json"][0]["evidence"]


def test_period_excludes_outside_and_crossing_records(client, db_session, auth_headers_factory, provider_override):
    product = add_product(db_session)
    add_record(db_session, product, impressions=100, clicks=10)
    add_record(db_session, product, start="2026-08-31T12:00:00+00:00", end="2026-09-01T12:00:00+00:00", impressions=500, clicks=50)
    add_record(db_session, product, start="2026-08-01T00:00:00+00:00", end="2026-08-02T00:00:00+00:00", impressions=900, clicks=90)
    provider = CapturingProvider()
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    context = response.json()["input_context_json"]
    assert context["aggregated_performance"]["total_impressions"] == 100
    assert context["review_period"]["included_count"] == 1
    assert context["review_period"]["excluded_count"] == 1


def test_no_data_stops_before_provider(client, db_session, auth_headers_factory, provider_override):
    product = add_product(db_session)
    provider = FailingProvider()
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_performance_data"
    assert provider.calls == 0


@pytest.mark.parametrize("end", ["2026-09-01T00:00:00+00:00", "2026-08-31T00:00:00+00:00"])
def test_invalid_period_is_422(client, db_session, auth_headers_factory, end):
    product = add_product(db_session)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN), end=end)
    assert response.status_code == 422


def test_viewer_cannot_generate_or_edit_but_can_query(client, db_session, auth_headers_factory, provider_override):
    product = add_product(db_session)
    add_record(db_session, product)
    provider_override(CapturingProvider())
    admin = auth_headers_factory(UserRole.ADMIN)
    report = generate(client, product, admin).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert generate(client, product, viewer).status_code == 403
    assert client.patch(
        f"/api/v1/products/{product.id}/review-reports/{report['id']}",
        json={"summary_text": "viewer edit"}, headers=viewer,
    ).status_code == 403
    assert client.get(
        f"/api/v1/products/{product.id}/review-reports/{report['id']}", headers=viewer
    ).status_code == 200


def test_missing_product_is_404(client, auth_headers_factory, provider_override):
    provider_override(CapturingProvider())
    response = client.post(
        "/api/v1/products/999/review-reports/generate",
        json={"period_start": "2026-09-01T00:00:00+00:00", "period_end": "2026-09-05T00:00:00+00:00"},
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("provider", [FailingProvider(), CapturingProvider({"summary": "incomplete"})])
def test_provider_or_schema_failure_does_not_persist(
    client, db_session, auth_headers_factory, provider_override, provider
):
    product = add_product(db_session)
    add_record(db_session, product)
    provider_override(provider)
    response = generate(client, product, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(ReviewReport)) == 0


def test_operator_edits_business_fields_and_protected_fields_are_rejected(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    add_record(db_session, product)
    provider_override(CapturingProvider())
    report = generate(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    operator = auth_headers_factory(UserRole.OPERATOR)
    response = client.patch(
        f"/api/v1/products/{product.id}/review-reports/{report['id']}",
        json={
            "summary_text": "人工修订摘要",
            "insights_json": [{"title": "修订", "finding": "人工判断", "evidence": "系统汇总数据"}],
            "problem_judgements_json": [{"problem": "待验证", "evidence": "数据有限", "severity": "low"}],
            "next_actions_json": [{"action": "继续观察", "rationale": "积累数据", "priority": "medium"}],
        }, headers=operator,
    )
    assert response.status_code == 200
    assert response.json()["summary_text"] == "人工修订摘要"
    for field, value in (
        ("period_start", "2026-09-02T00:00:00+00:00"),
        ("input_context_json", {}), ("provider_name", "forged"), ("product_id", 999),
    ):
        rejected = client.patch(
            f"/api/v1/products/{product.id}/review-reports/{report['id']}",
            json={field: value}, headers=operator,
        )
        assert rejected.status_code == 422


def test_product_report_mismatch_is_404(client, db_session, auth_headers_factory, provider_override):
    product_a = add_product(db_session, "a")
    product_b = add_product(db_session, "b")
    add_record(db_session, product_a)
    provider_override(CapturingProvider())
    headers = auth_headers_factory(UserRole.OPERATOR)
    report = generate(client, product_a, headers).json()
    assert client.get(
        f"/api/v1/products/{product_b.id}/review-reports/{report['id']}", headers=headers
    ).status_code == 404
    assert client.patch(
        f"/api/v1/products/{product_b.id}/review-reports/{report['id']}",
        json={"summary_text": "cross product"}, headers=headers,
    ).status_code == 404


def test_list_filters_paginates_and_orders_latest_first(
    client, db_session, auth_headers_factory, provider_override
):
    product = add_product(db_session)
    add_record(db_session, product)
    provider_override(CapturingProvider())
    headers = auth_headers_factory(UserRole.ADMIN)
    first = generate(client, product, headers).json()
    second = generate(client, product, headers).json()
    response = client.get(
        f"/api/v1/products/{product.id}/review-reports",
        params={
            "period_start_from": "2026-09-01T00:00:00+00:00",
            "period_end_to": "2026-09-05T00:00:00+00:00",
            "page": 1, "page_size": 1,
        }, headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["id"] == second["id"]
    assert first["id"] != second["id"]
