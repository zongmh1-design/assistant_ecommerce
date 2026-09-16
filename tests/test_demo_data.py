"""Admin-only resumable demo initialization and cross-object consistency tests."""

import json

import pytest
from sqlalchemy import func, select

from app.models.ad_experiment import AdExperiment, AdExperimentStatus
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.competitor import Competitor
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset
from app.models.generation_job import GenerationJob, GenerationJobStatus
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.performance_record import PerformanceRecord
from app.models.product import Product
from app.models.product_diagnosis import ProductDiagnosis
from app.models.product_sku import ProductSku
from app.models.promotion_link import PromotionLink, PromotionLinkStatus
from app.models.review_report import ReviewReport
from app.models.store import Store
from app.models.user import User, UserRole
from app.services.demo_data_service import DEMO_STORE_NAME


def initialize(client, headers):
    return client.post("/api/v1/workspace/demo-data", headers=headers)


def test_admin_creates_complete_demo_chain_with_service_invariants(
    client, db_session, auth_headers_factory
):
    response = initialize(client, auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed", body
    assert body["failed_step"] is None
    assert len(body["sku_ids"]) == 2
    assert len(body["performance_record_ids"]) == 3

    product_id = body["product_id"]
    store = db_session.get(Store, body["store_id"])
    product = db_session.get(Product, product_id)
    assert store.store_name == DEMO_STORE_NAME
    assert "Demo" in product.name

    skus = list(db_session.scalars(select(ProductSku).where(ProductSku.product_id == product_id)))
    assert len(skus) == 2
    inventories = list(db_session.scalars(select(InventoryItem).where(
        InventoryItem.sku_id.in_([sku.id for sku in skus])
    )))
    assert sorted(item.stock_qty for item in inventories) == [50, 80]
    assert db_session.scalar(select(func.count()).select_from(InventoryMovement).where(
        InventoryMovement.sku_id.in_([sku.id for sku in skus])
    )) >= 4  # initial + inbound for each SKU

    assert db_session.scalar(select(func.count()).select_from(Competitor).where(Competitor.product_id == product_id)) == 2
    assert db_session.scalar(select(func.count()).select_from(ProductDiagnosis).where(ProductDiagnosis.product_id == product_id)) == 1
    plans = list(db_session.scalars(select(CreativePlan).where(CreativePlan.product_id == product_id)))
    assert sum(plan.plan_type == CreativePlanType.MAIN_IMAGE for plan in plans) == 3
    assert sum(plan.plan_type == CreativePlanType.VIDEO_SCRIPT for plan in plans) == 3
    assert sum(plan.status == CreativePlanStatus.SELECTED and plan.plan_type == CreativePlanType.MAIN_IMAGE for plan in plans) == 1
    assert sum(plan.status == CreativePlanStatus.SELECTED and plan.plan_type == CreativePlanType.VIDEO_SCRIPT for plan in plans) == 1

    jobs = list(db_session.scalars(select(GenerationJob).where(GenerationJob.product_id == product_id)))
    assert len(jobs) == 2
    assert all(job.job_status == GenerationJobStatus.SUCCEEDED for job in jobs)
    assets = list(db_session.scalars(select(GeneratedAsset).where(GeneratedAsset.product_id == product_id)))
    assert len(assets) == 2
    assert all(asset.review_status == AssetReviewStatus.APPROVED for asset in assets)

    link = db_session.get(PromotionLink, body["promotion_link_id"])
    assert link.status == PromotionLinkStatus.ACTIVE
    assert link.click_count == 3
    recommendation = db_session.get(AdRecommendation, body["ad_recommendation_id"])
    assert recommendation.confirm_status == AdRecommendationConfirmStatus.CONFIRMED
    assert recommendation.confirmed_by is not None
    experiment = db_session.get(AdExperiment, body["ad_experiment_id"])
    assert experiment.experiment_status == AdExperimentStatus.FINISHED
    assert len(body["performance_record_ids"]) == db_session.scalar(
        select(func.count()).select_from(PerformanceRecord).where(PerformanceRecord.product_id == product_id)
    )
    assert db_session.get(ReviewReport, body["review_report_id"]).product_id == product_id


@pytest.mark.parametrize("role", [UserRole.OPERATOR, UserRole.VIEWER])
def test_non_admin_cannot_initialize(client, auth_headers_factory, role):
    assert initialize(client, auth_headers_factory(role)).status_code == 403


def test_missing_token_cannot_initialize(client):
    assert initialize(client, {}).status_code == 401


def test_repeat_returns_stable_ids_without_duplicate_business_graph(
    client, db_session, auth_headers_factory
):
    headers = auth_headers_factory(UserRole.ADMIN)
    first = initialize(client, headers).json()
    counts_before = {
        model: db_session.scalar(select(func.count()).select_from(model))
        for model in (Store, Product, ProductSku, Competitor, ProductDiagnosis, CreativePlan,
                      GenerationJob, GeneratedAsset, PromotionLink, AdRecommendation,
                      AdExperiment, PerformanceRecord, ReviewReport)
    }
    second_response = initialize(client, headers)
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["status"] == "already_exists", second
    for field in (
        "store_id", "product_id", "sku_ids", "selected_main_image_plan_id",
        "selected_video_plan_id", "image_job_id", "video_job_id",
        "approved_image_asset_id", "approved_video_asset_id", "promotion_link_id",
        "ad_recommendation_id", "ad_experiment_id", "performance_record_ids",
        "review_report_id",
    ):
        assert second[field] == first[field]
    for model, count in counts_before.items():
        assert db_session.scalar(select(func.count()).select_from(model)) == count


def test_every_demo_business_object_belongs_to_same_product(
    client, db_session, auth_headers_factory
):
    body = initialize(client, auth_headers_factory(UserRole.ADMIN)).json()
    product_id = body["product_id"]
    for model in (
        ProductSku, Competitor, ProductDiagnosis, CreativePlan, GenerationJob,
        GeneratedAsset, PromotionLink, AdRecommendation, AdExperiment,
        PerformanceRecord, ReviewReport,
    ):
        values = set(db_session.scalars(select(model.product_id)))
        assert values == {product_id}, model.__name__


def test_demo_endpoint_does_not_create_users_or_return_sensitive_values(
    client, db_session, auth_headers_factory
):
    headers = auth_headers_factory(UserRole.ADMIN)
    user_count = db_session.scalar(select(func.count()).select_from(User))
    response = initialize(client, headers)
    assert db_session.scalar(select(func.count()).select_from(User)) == user_count
    serialized = json.dumps(response.json()).lower()
    for forbidden in ("password", "jwt", "api_key", "authorization", "secret"):
        assert forbidden not in serialized
