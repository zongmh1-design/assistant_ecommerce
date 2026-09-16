"""GeneratedAsset synchronization, versioning, review and permission tests."""

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import (
    AssetReviewStatus,
    GeneratedAsset,
    GeneratedAssetType,
)
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.product import Product
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.repositories.generated_asset_repository import GeneratedAssetRepository


def _create_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Asset Store {suffix}", platform=Platform.OTHER)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=f"Asset Product {suffix}",
        platform=Platform.OTHER,
        price=Decimal("88.00"),
        selling_points=["known benefit"],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_plan(
    db: Session,
    product: Product,
    plan_type: CreativePlanType,
    suffix: str = "a",
) -> CreativePlan:
    plan = CreativePlan(
        product_id=product.id,
        plan_type=plan_type,
        title=f"{plan_type.value} {suffix}",
        content_json={"fixture": suffix},
        rationale_text="Test source plan",
        status=CreativePlanStatus.SELECTED,
        input_context_json={"product": {"name": product.name}, "diagnosis": None},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _valid_result(kind: GenerationJobKind, marker: str = "a") -> dict[str, Any]:
    if kind == GenerationJobKind.IMAGE:
        return {
            "asset_type": "image",
            "mock": True,
            "url": f"mock://images/{marker}.png",
            "width": 1024,
            "height": 1024,
            "generator": "mock_image_generator",
        }
    return {
        "asset_type": "video",
        "mock": True,
        "url": f"mock://videos/{marker}.mp4",
        "duration_sec": 15,
        "generator": "mock_video_generator",
    }


def _create_job(
    db: Session,
    product: Product,
    plan: CreativePlan,
    kind: GenerationJobKind,
    *,
    status: GenerationJobStatus = GenerationJobStatus.SUCCEEDED,
    result: dict[str, Any] | None = None,
) -> GenerationJob:
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=kind,
        job_status=status,
        attempts=1 if status != GenerationJobStatus.PENDING else 0,
        result_json=_valid_result(kind, str(plan.id)) if result is None and status == GenerationJobStatus.SUCCEEDED else result,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _sync(client, product: Product, headers: dict[str, str]):
    return client.post(f"/api/v1/products/{product.id}/assets/sync", headers=headers)


@pytest.mark.parametrize(
    ("plan_type", "kind", "expected"),
    [
        (CreativePlanType.MAIN_IMAGE, GenerationJobKind.IMAGE, "image"),
        (CreativePlanType.VIDEO_SCRIPT, GenerationJobKind.VIDEO, "video"),
    ],
)
def test_succeeded_image_and_video_jobs_sync_to_pending_assets(
    client, db_session, auth_headers_factory, plan_type, kind, expected
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, plan_type)
    job = _create_job(db_session, product, plan, kind)
    response = _sync(client, product, auth_headers_factory(UserRole.OPERATOR))
    assert response.status_code == 200
    assert response.json()["synced_count"] == 1
    asset = db_session.scalar(
        select(GeneratedAsset).where(GeneratedAsset.generation_job_id == job.id)
    )
    assert asset is not None
    assert asset.asset_type.value == expected
    assert asset.review_status == AssetReviewStatus.PENDING
    assert asset.version_no == 1
    assert asset.model_name == f"mock_{expected}_generator"
    if kind == GenerationJobKind.IMAGE:
        assert (asset.width, asset.height, asset.duration_sec) == (1024, 1024, None)
    else:
        assert (asset.width, asset.height, asset.duration_sec) == (None, None, 15)


def test_result_model_name_takes_precedence_over_generator_name(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    result = _valid_result(GenerationJobKind.IMAGE)
    result["model_name"] = "configured-image-model"
    job = _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        result=result,
    )
    _sync(client, product, auth_headers_factory(UserRole.ADMIN))
    asset = db_session.scalar(
        select(GeneratedAsset).where(GeneratedAsset.generation_job_id == job.id)
    )
    assert asset is not None
    assert asset.model_name == "configured-image-model"


@pytest.mark.parametrize(
    "status",
    [
        GenerationJobStatus.PENDING,
        GenerationJobStatus.RUNNING,
        GenerationJobStatus.FAILED,
        GenerationJobStatus.CANCELLED,
        GenerationJobStatus.TIMEOUT,
    ],
)
def test_non_succeeded_jobs_are_not_synchronized(
    client, db_session, auth_headers_factory, status
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        status=status,
        result=_valid_result(GenerationJobKind.IMAGE),
    )
    body = _sync(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    assert body == {
        "synced_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "asset_ids": [],
        "failures": [],
    }
    assert db_session.scalar(select(func.count()).select_from(GeneratedAsset)) == 0


@pytest.mark.parametrize(
    "result",
    [
        None,
        {
            "asset_type": "image",
            "mock": True,
            "url": "mock://images/missing-width.png",
            "height": 1024,
            "generator": "mock_image_generator",
        },
        {
            "asset_type": "video",
            "mock": True,
            "url": "mock://videos/missing-duration.mp4",
            "generator": "mock_video_generator",
        },
        {
            "asset_type": "video",
            "mock": True,
            "url": "mock://videos/wrong-type.mp4",
            "duration_sec": 15,
            "generator": "mock_video_generator",
        },
    ],
)
def test_missing_or_invalid_image_result_does_not_create_asset(
    client, db_session, auth_headers_factory, result
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    job = _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        result={"invalid": True} if result is None else result,
    )
    if result is None:
        job.result_json = None
        db_session.commit()
    body = _sync(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    assert body["failed_count"] == 1
    assert body["failures"][0]["code"] == "invalid_generation_result"
    assert db_session.scalar(select(func.count()).select_from(GeneratedAsset)) == 0
    db_session.refresh(job)
    assert job.job_status == GenerationJobStatus.SUCCEEDED


def test_invalid_video_result_does_not_create_asset(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.VIDEO_SCRIPT)
    _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.VIDEO,
        result={
            "asset_type": "video",
            "mock": True,
            "url": "mock://videos/invalid.mp4",
            "generator": "mock_video_generator",
        },
    )
    body = _sync(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    assert body["failed_count"] == 1
    assert db_session.scalar(select(func.count()).select_from(GeneratedAsset)) == 0


def test_bad_job_does_not_block_valid_job(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    bad = _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        result={"asset_type": "image"},
    )
    good = _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    body = _sync(client, product, auth_headers_factory(UserRole.OPERATOR)).json()
    assert body["synced_count"] == 1
    assert body["failed_count"] == 1
    assert body["asset_ids"]
    assert body["failures"][0]["job_id"] == bad.id
    asset = db_session.scalar(
        select(GeneratedAsset).where(GeneratedAsset.generation_job_id == good.id)
    )
    assert asset is not None


def test_sync_is_idempotent_and_job_id_is_unique(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    job = _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    headers = auth_headers_factory(UserRole.ADMIN)
    first = _sync(client, product, headers).json()
    second = _sync(client, product, headers).json()
    assert first["synced_count"] == 1
    assert second["synced_count"] == 0
    assert second["skipped_count"] == 1
    assert db_session.scalar(select(func.count()).select_from(GeneratedAsset)) == 1

    duplicate = GeneratedAsset(
        product_id=product.id,
        creative_plan_id=plan.id,
        generation_job_id=job.id,
        asset_type=GeneratedAssetType.IMAGE,
        asset_url="mock://images/duplicate.png",
        model_name="mock_image_generator",
        width=1024,
        height=1024,
        review_status=AssetReviewStatus.PENDING,
        version_no=2,
        tags_json=[],
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_versions_increment_per_plan_and_type(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    image_plan_a = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE, "a")
    image_plan_a.status = CreativePlanStatus.ARCHIVED
    db_session.commit()
    image_plan_b = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE, "b")
    video_plan = _create_plan(db_session, product, CreativePlanType.VIDEO_SCRIPT, "v")
    jobs = [
        _create_job(db_session, product, image_plan_a, GenerationJobKind.IMAGE, result=_valid_result(GenerationJobKind.IMAGE, "a1")),
        _create_job(db_session, product, image_plan_a, GenerationJobKind.IMAGE, result=_valid_result(GenerationJobKind.IMAGE, "a2")),
        _create_job(db_session, product, image_plan_b, GenerationJobKind.IMAGE, result=_valid_result(GenerationJobKind.IMAGE, "b1")),
        _create_job(db_session, product, video_plan, GenerationJobKind.VIDEO, result=_valid_result(GenerationJobKind.VIDEO, "v1")),
    ]
    body = _sync(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    assert body["synced_count"] == 4
    assets = {
        asset.generation_job_id: asset
        for asset in db_session.scalars(select(GeneratedAsset))
    }
    assert [assets[jobs[0].id].version_no, assets[jobs[1].id].version_no] == [1, 2]
    assert assets[jobs[2].id].version_no == 1
    assert assets[jobs[3].id].version_no == 1


def test_version_unique_constraint_is_enforced(db_session):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    job_a = _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    job_b = _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    common = {
        "product_id": product.id,
        "creative_plan_id": plan.id,
        "asset_type": GeneratedAssetType.IMAGE,
        "model_name": "mock_image_generator",
        "width": 1024,
        "height": 1024,
        "review_status": AssetReviewStatus.PENDING,
        "version_no": 1,
        "tags_json": [],
    }
    db_session.add_all(
        [
            GeneratedAsset(generation_job_id=job_a.id, asset_url="mock://a", **common),
            GeneratedAsset(generation_job_id=job_b.id, asset_url="mock://b", **common),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_query_filters_pagination_detail_and_product_boundary(
    client, db_session, auth_headers_factory
):
    product_a = _create_product(db_session, "a")
    product_b = _create_product(db_session, "b")
    image_plan = _create_plan(db_session, product_a, CreativePlanType.MAIN_IMAGE)
    video_plan = _create_plan(db_session, product_a, CreativePlanType.VIDEO_SCRIPT)
    _create_job(db_session, product_a, image_plan, GenerationJobKind.IMAGE)
    _create_job(db_session, product_a, video_plan, GenerationJobKind.VIDEO)
    headers = auth_headers_factory(UserRole.ADMIN)
    _sync(client, product_a, headers)
    image_asset = db_session.scalar(
        select(GeneratedAsset).where(GeneratedAsset.asset_type == GeneratedAssetType.IMAGE)
    )
    assert image_asset is not None
    image_asset.review_status = AssetReviewStatus.APPROVED
    db_session.commit()

    base = f"/api/v1/products/{product_a.id}/assets"
    assert client.get(f"{base}?asset_type=image", headers=headers).json()["total"] == 1
    assert client.get(f"{base}?review_status=approved", headers=headers).json()["total"] == 1
    assert client.get(
        f"{base}?creative_plan_id={image_plan.id}", headers=headers
    ).json()["total"] == 1
    page = client.get(f"{base}?page=1&page_size=1", headers=headers).json()
    assert page["total"] == 2
    assert page["items"][0]["asset_type"] == "video"
    assert client.get(f"{base}/{image_asset.id}", headers=headers).status_code == 200
    assert client.get(
        f"/api/v1/products/{product_b.id}/assets/{image_asset.id}", headers=headers
    ).status_code == 404
    assert client.get(
        "/api/v1/products/9999/assets", headers=headers
    ).status_code == 404


def test_operator_reviews_edits_metadata_and_can_reverse_decision(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    admin = auth_headers_factory(UserRole.ADMIN)
    asset_id = _sync(client, product, admin).json()["asset_ids"][0]
    path = f"/api/v1/products/{product.id}/assets/{asset_id}"
    operator = auth_headers_factory(UserRole.OPERATOR)
    approved = client.patch(
        path,
        headers=operator,
        json={
            "review_status": "approved",
            "usage_scene": "首页主图",
            "score": 100,
            "tags_json": [" 主图 ", "", "年轻用户", "主图"],
            "remark": "人工确认",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["tags_json"] == ["主图", "年轻用户"]
    assert approved.json()["score"] == 100
    rejected = client.patch(path, headers=operator, json={"review_status": "rejected"})
    assert rejected.json()["review_status"] == "rejected"
    reapproved = client.patch(path, headers=operator, json={"review_status": "approved"})
    assert reapproved.json()["review_status"] == "approved"
    back_to_pending = client.patch(
        path, headers=operator, json={"review_status": "pending"}
    )
    assert back_to_pending.status_code == 409
    assert back_to_pending.json()["error"]["code"] == (
        "invalid_asset_review_status_transition"
    )


def test_pending_can_be_rejected_and_score_boundaries_are_enforced(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    headers = auth_headers_factory(UserRole.ADMIN)
    asset_id = _sync(client, product, headers).json()["asset_ids"][0]
    path = f"/api/v1/products/{product.id}/assets/{asset_id}"
    assert client.patch(
        path, headers=headers, json={"review_status": "rejected", "score": 0}
    ).status_code == 200
    for score in (-1, 101):
        assert client.patch(path, headers=headers, json={"score": score}).status_code == 422


def test_viewer_can_query_but_cannot_sync_or_update(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    admin = auth_headers_factory(UserRole.ADMIN)
    asset_id = _sync(client, product, admin).json()["asset_ids"][0]
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert _sync(client, product, viewer).status_code == 403
    path = f"/api/v1/products/{product.id}/assets/{asset_id}"
    assert client.get(path, headers=viewer).status_code == 200
    assert client.patch(
        path, headers=viewer, json={"review_status": "approved"}
    ).status_code == 403


@pytest.mark.parametrize(
    "field",
    [
        "product_id",
        "creative_plan_id",
        "generation_job_id",
        "asset_type",
        "asset_url",
        "model_name",
        "version_no",
        "created_at",
    ],
)
def test_protected_asset_fields_cannot_be_modified(
    client, db_session, auth_headers_factory, field
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    _create_job(db_session, product, plan, GenerationJobKind.IMAGE)
    headers = auth_headers_factory(UserRole.ADMIN)
    asset_id = _sync(client, product, headers).json()["asset_ids"][0]
    response = client.patch(
        f"/api/v1/products/{product.id}/assets/{asset_id}",
        headers=headers,
        json={field: 999},
    )
    assert response.status_code == 422


def test_asset_persistence_failure_is_isolated(
    client, db_session, auth_headers_factory, monkeypatch
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    bad_job = _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        result=_valid_result(GenerationJobKind.IMAGE, "bad"),
    )
    good_job = _create_job(
        db_session,
        product,
        plan,
        GenerationJobKind.IMAGE,
        result=_valid_result(GenerationJobKind.IMAGE, "good"),
    )
    original_add = GeneratedAssetRepository.add

    def fail_one(repository, asset):
        if asset.generation_job_id == bad_job.id:
            raise RuntimeError("simulated asset insert failure")
        return original_add(repository, asset)

    monkeypatch.setattr(GeneratedAssetRepository, "add", fail_one)
    body = _sync(client, product, auth_headers_factory(UserRole.ADMIN)).json()
    assert body["synced_count"] == 1
    assert body["failed_count"] == 1
    assert body["failures"][0]["job_id"] == bad_job.id
    assert db_session.scalar(
        select(func.count())
        .select_from(GeneratedAsset)
        .where(GeneratedAsset.generation_job_id == bad_job.id)
    ) == 0
    assert db_session.scalar(
        select(func.count())
        .select_from(GeneratedAsset)
        .where(GeneratedAsset.generation_job_id == good_job.id)
    ) == 1
