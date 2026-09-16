"""Manual performance entry, metric calculation, relation and query tests."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.ad_experiment import AdExperiment, AdExperimentStatus
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset, GeneratedAssetType
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.product import Product, ProductStatus
from app.models.promotion_link import PromotionLink, PromotionLinkStatus
from app.models.store import Platform, Store
from app.models.user import UserRole


def add_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Performance Store {suffix}", platform=Platform.JD)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=f"Performance Product {suffix}",
        platform=Platform.JD,
        category="家居",
        price=Decimal("199.90"),
        target_audience="年轻家庭",
        selling_points=["轻量", "耐用"],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_plan(db: Session, product: Product, suffix: str = "a") -> CreativePlan:
    plan = CreativePlan(
        product_id=product.id,
        plan_type=CreativePlanType.MAIN_IMAGE,
        title=f"Performance Plan {suffix}",
        content_json={"core_copy": "轻量耐用"},
        rationale_text="fixture",
        status=CreativePlanStatus.DRAFT,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def add_asset(db: Session, product: Product, suffix: str = "a") -> GeneratedAsset:
    plan = add_plan(db, product, suffix)
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.SUCCEEDED,
        attempts=1,
        result_json={
            "asset_type": "image",
            "url": f"mock://performance-{suffix}.png",
            "width": 1024,
            "height": 1024,
        },
    )
    db.add(job)
    db.flush()
    asset = GeneratedAsset(
        product_id=product.id,
        creative_plan_id=plan.id,
        generation_job_id=job.id,
        asset_type=GeneratedAssetType.IMAGE,
        asset_url=f"mock://performance-{suffix}.png",
        model_name="mock_image_generator",
        width=1024,
        height=1024,
        review_status=AssetReviewStatus.APPROVED,
        version_no=1,
        tags_json=["主图"],
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def add_link(
    db: Session, product: Product, suffix: str = "a", click_count: int = 0
) -> PromotionLink:
    link = PromotionLink(
        product_id=product.id,
        link_name=f"Performance Link {suffix}",
        target_url="https://example.com/product",
        tracking_code=f"performance-{product.id}-{suffix}",
        utm_json={"utm_source": "manual"},
        status=PromotionLinkStatus.ACTIVE,
        click_count=click_count,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def add_experiment(
    db: Session,
    product: Product,
    status: AdExperimentStatus = AdExperimentStatus.RUNNING,
    suffix: str = "a",
) -> AdExperiment:
    recommendation = AdRecommendation(
        product_id=product.id,
        summary_text="人工确认建议",
        objective_text="观察真实数据",
        audience_segments_json=[],
        budget_plan_json={
            "total_budget": "100.00",
            "currency": "CNY",
            "allocation": [],
            "rationale": "fixture",
        },
        creative_tests_json=[],
        bid_strategy_json={
            "strategy_name": "人工",
            "rationale": "fixture",
            "constraints": [],
        },
        risk_controls_json=[],
        next_steps_json=[],
        confirm_status=AdRecommendationConfirmStatus.CONFIRMED,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(recommendation)
    db.flush()
    experiment = AdExperiment(
        product_id=product.id,
        ad_recommendation_id=recommendation.id,
        experiment_name=f"Performance Experiment {suffix}",
        target_text="记录结果",
        audience_text="已知人群",
        budget_amount=Decimal("100.00"),
        success_metric_text="观察实际指标",
        hypothesis_text="待验证假设",
        experiment_status=status,
        input_context_json={"product": {"name": product.name}},
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def valid_payload(**overrides):
    payload = {
        "period_start": "2026-09-01T00:00:00+00:00",
        "period_end": "2026-09-02T00:00:00+00:00",
        "impressions": 1000,
        "clicks": 50,
        "conversions": 5,
        "spend": "100.00",
        "revenue": "150.00",
        "notes": "manual entry",
    }
    payload.update(overrides)
    return payload


def create(client, product: Product, headers, **overrides):
    return client.post(
        f"/api/v1/products/{product.id}/performance-records",
        json=valid_payload(**overrides),
        headers=headers,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_create_with_decimal_metrics(
    client, db_session, auth_headers_factory, role
):
    product = add_product(db_session)
    response = create(client, product, auth_headers_factory(role))
    assert response.status_code == 201
    body = response.json()
    assert body["ctr"] == "0.050000"
    assert body["conversion_rate"] == "0.100000"
    assert body["roi"] == "0.500000"
    assert body["spend"] == "100.00"
    assert body["revenue"] == "150.00"


def test_viewer_cannot_create_but_can_query(client, db_session, auth_headers_factory):
    product = add_product(db_session)
    admin = auth_headers_factory(UserRole.ADMIN)
    record = create(client, product, admin).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert create(client, product, viewer).status_code == 403
    assert client.get(
        f"/api/v1/products/{product.id}/performance-records/{record['id']}",
        headers=viewer,
    ).status_code == 200


def test_missing_product_is_404(client, auth_headers_factory):
    response = client.post(
        "/api/v1/products/999/performance-records",
        json=valid_payload(),
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"period_end": "2026-09-01T00:00:00+00:00"},
        {"period_end": "2026-08-31T00:00:00+00:00"},
        {"impressions": -1},
        {"clicks": -1},
        {"conversions": -1},
        {"spend": "-0.01"},
        {"revenue": "-0.01"},
        {"impressions": 10, "clicks": 11},
        {"clicks": 2, "conversions": 3},
    ],
)
def test_invalid_period_raw_counts_or_money_is_rejected(
    client, db_session, auth_headers_factory, overrides
):
    product = add_product(db_session)
    response = create(
        client, product, auth_headers_factory(UserRole.ADMIN), **overrides
    )
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["ctr", "conversion_rate", "roi"])
def test_client_cannot_submit_derived_metrics(
    client, db_session, auth_headers_factory, field
):
    product = add_product(db_session)
    response = create(
        client, product, auth_headers_factory(UserRole.ADMIN), **{field: "0.99"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        (
            {"impressions": 1000, "clicks": 50, "conversions": 5,
             "spend": "100.00", "revenue": "150.00"},
            ("0.050000", "0.100000", "0.500000"),
        ),
        (
            {"spend": "100.00", "revenue": "50.00"},
            ("0.050000", "0.100000", "-0.500000"),
        ),
        (
            {"spend": "0.00", "revenue": "50.00"},
            ("0.050000", "0.100000", None),
        ),
        (
            {"impressions": 0, "clicks": 0, "conversions": 0},
            ("0.000000", "0.000000", "0.500000"),
        ),
    ],
)
def test_metric_formulas_and_zero_division(
    client, db_session, auth_headers_factory, metrics, expected
):
    product = add_product(db_session)
    response = create(
        client, product, auth_headers_factory(UserRole.ADMIN), **metrics
    )
    assert response.status_code == 201
    body = response.json()
    assert (body["ctr"], body["conversion_rate"], body["roi"]) == expected


def test_all_optional_relations_must_belong_to_product(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session, "a")
    other = add_product(db_session, "b")
    foreign_plan = add_plan(db_session, other)
    foreign_asset = add_asset(db_session, other, "b")
    foreign_link = add_link(db_session, other, "b")
    foreign_experiment = add_experiment(db_session, other, suffix="b")
    headers = auth_headers_factory(UserRole.ADMIN)
    for field, relation_id in (
        ("creative_plan_id", foreign_plan.id),
        ("generated_asset_id", foreign_asset.id),
        ("promotion_link_id", foreign_link.id),
        ("experiment_id", foreign_experiment.id),
    ):
        assert create(client, product, headers, **{field: relation_id}).status_code == 404


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (AdExperimentStatus.DRAFT, 409),
        (AdExperimentStatus.CONFIRMED, 409),
        (AdExperimentStatus.CANCELLED, 409),
        (AdExperimentStatus.RUNNING, 201),
        (AdExperimentStatus.FINISHED, 201),
    ],
)
def test_experiment_must_be_running_or_finished(
    client, db_session, auth_headers_factory, status, expected
):
    product = add_product(db_session)
    experiment = add_experiment(db_session, product, status)
    response = create(
        client,
        product,
        auth_headers_factory(UserRole.OPERATOR),
        experiment_id=experiment.id,
    )
    assert response.status_code == expected


def test_update_recalculates_all_metrics_and_viewer_is_read_only(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    admin = auth_headers_factory(UserRole.ADMIN)
    record = create(client, product, admin).json()
    url = f"/api/v1/products/{product.id}/performance-records/{record['id']}"
    response = client.patch(
        url,
        json={
            "impressions": 2000,
            "clicks": 100,
            "conversions": 20,
            "spend": "200.00",
            "revenue": "100.00",
        },
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ctr"] == "0.050000"
    assert body["conversion_rate"] == "0.200000"
    assert body["roi"] == "-0.500000"
    assert client.patch(
        url,
        json={"notes": "viewer cannot edit"},
        headers=auth_headers_factory(UserRole.VIEWER),
    ).status_code == 403


def test_update_revalidates_relation_and_product_record_mismatch(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session, "a")
    other = add_product(db_session, "b")
    foreign_link = add_link(db_session, other)
    headers = auth_headers_factory(UserRole.ADMIN)
    record = create(client, product, headers).json()
    assert client.patch(
        f"/api/v1/products/{product.id}/performance-records/{record['id']}",
        json={"promotion_link_id": foreign_link.id},
        headers=headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/products/{other.id}/performance-records/{record['id']}",
        json={"notes": "wrong product"},
        headers=headers,
    ).status_code == 404


def test_query_filters_pagination_time_and_detail(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session, "a")
    other = add_product(db_session, "b")
    asset = add_asset(db_session, product)
    link = add_link(db_session, product)
    experiment = add_experiment(db_session, product)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = create(
        client, product, headers,
        period_start="2026-09-01T00:00:00+00:00",
        period_end="2026-09-02T00:00:00+00:00",
        generated_asset_id=asset.id,
        promotion_link_id=link.id,
        experiment_id=experiment.id,
    ).json()
    second = create(
        client, product, headers,
        period_start="2026-09-03T00:00:00+00:00",
        period_end="2026-09-04T00:00:00+00:00",
    ).json()
    viewer = auth_headers_factory(UserRole.VIEWER)
    base = f"/api/v1/products/{product.id}/performance-records"
    response = client.get(
        base
        + f"?experiment_id={experiment.id}&generated_asset_id={asset.id}"
        + f"&promotion_link_id={link.id}&period_start_from=2026-09-01T00:00:00Z"
        + "&period_end_to=2026-09-02T00:00:00Z&page=1&page_size=1",
        headers=viewer,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first["id"]
    unfiltered = client.get(base, headers=viewer).json()
    assert [item["id"] for item in unfiltered["items"][:2]] == [second["id"], first["id"]]
    assert client.get(f"{base}/{first['id']}", headers=viewer).status_code == 200
    assert client.get(
        f"/api/v1/products/{other.id}/performance-records/{first['id']}",
        headers=viewer,
    ).status_code == 404


def test_promotion_click_count_is_not_used_as_period_clicks(
    client, db_session, auth_headers_factory
):
    product = add_product(db_session)
    link = add_link(db_session, product, click_count=999)
    response = create(
        client,
        product,
        auth_headers_factory(UserRole.ADMIN),
        promotion_link_id=link.id,
        impressions=10,
        clicks=2,
        conversions=1,
    )
    assert response.status_code == 201
    assert response.json()["clicks"] == 2
    assert response.json()["ctr"] == "0.200000"
