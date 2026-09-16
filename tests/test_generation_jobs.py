"""Generation job lifecycle, permissions, events and transaction boundaries."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.generation.dependencies import get_image_generator, get_video_generator
from app.generation.media_generator import MediaGeneratorError
from app.generation.mock_generators import MockImageGenerator
from app.main import app
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generation_job import (
    GenerationJob,
    GenerationJobEvent,
    GenerationJobEventType,
    GenerationJobKind,
    GenerationJobStatus,
)
from app.models.product import Product
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.repositories.generation_job_event_repository import GenerationJobEventRepository
from app.services.generation_job_service import GenerationJobService


class FailingGenerator:
    def generate(self, _: object) -> dict[str, Any]:
        raise MediaGeneratorError("deterministic generator failure")


class ObservingImageGenerator:
    def __init__(self, db: Session, commit_count: list[int]) -> None:
        self.db = db
        self.commit_count = commit_count
        self.saw_running = False
        self.saw_started_event = False

    def generate(self, generation_input: object) -> dict[str, Any]:
        job_id = generation_input.job_id  # type: ignore[attr-defined]
        self.db.expire_all()
        job = self.db.get(GenerationJob, job_id)
        self.saw_running = (
            job is not None
            and job.job_status == GenerationJobStatus.RUNNING
            and job.attempts == 1
            and self.commit_count[0] >= 1
        )
        self.saw_started_event = self.db.scalar(
            select(func.count())
            .select_from(GenerationJobEvent)
            .where(
                GenerationJobEvent.job_id == job_id,
                GenerationJobEvent.event_type == GenerationJobEventType.STARTED,
            )
        ) == 1
        return {
            "asset_type": "image",
            "mock": True,
            "url": f"mock://images/job-{job_id}.png",
            "width": 1024,
            "height": 1024,
            "generator": "observing_image_generator",
        }


def _create_product(db: Session, suffix: str = "a") -> Product:
    store = Store(store_name=f"Store {suffix}", platform=Platform.OTHER)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=f"Product {suffix}",
        platform=Platform.OTHER,
        price=Decimal("99.00"),
        selling_points=["clear benefit"],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_plan(
    db: Session,
    product: Product,
    plan_type: CreativePlanType,
    status: CreativePlanStatus = CreativePlanStatus.SELECTED,
) -> CreativePlan:
    content = (
        {
            "visual_structure": ["product centered"],
            "core_copy": ["clear core copy"],
            "highlighted_selling_points": ["clear benefit"],
        }
        if plan_type == CreativePlanType.MAIN_IMAGE
        else {
            "opening_hook": "Opening hook",
            "storyboard": [
                {
                    "scene_no": 1,
                    "visual": "Product close-up",
                    "duration_hint": "5 seconds",
                    "voiceover": "Known product benefit",
                }
            ],
            "voiceover": ["Known product benefit"],
            "conversion_cta": "Review details",
        }
    )
    plan = CreativePlan(
        product_id=product.id,
        plan_type=plan_type,
        title=f"{plan_type.value} plan",
        content_json=content,
        rationale_text="Selected by an operator",
        status=status,
        input_context_json={"product": {"name": product.name}, "diagnosis": None},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _create_job(
    client: TestClient,
    product: Product,
    plan: CreativePlan,
    headers: dict[str, str],
    kind: GenerationJobKind,
):
    media_path = "images" if kind == GenerationJobKind.IMAGE else "videos"
    return client.post(
        f"/api/v1/products/{product.id}/creative-plans/{plan.id}/{media_path}/generate",
        headers=headers,
    )


@pytest.mark.parametrize(
    ("plan_type", "kind"),
    [
        (CreativePlanType.MAIN_IMAGE, GenerationJobKind.IMAGE),
        (CreativePlanType.VIDEO_SCRIPT, GenerationJobKind.VIDEO),
    ],
)
def test_selected_plan_creates_pending_job_and_created_event(
    client, db_session, auth_headers_factory, plan_type, kind
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, plan_type)
    response = _create_job(
        client, product, plan, auth_headers_factory(UserRole.OPERATOR), kind
    )
    assert response.status_code == 201
    body = response.json()
    assert body["job_kind"] == kind.value
    assert body["job_status"] == "pending"
    assert body["attempts"] == 0
    assert body["max_attempts"] == 3

    detail = client.get(
        f"/api/v1/products/{product.id}/generation-jobs/{body['id']}",
        headers=auth_headers_factory(UserRole.VIEWER),
    )
    assert detail.status_code == 200
    assert [item["event_type"] for item in detail.json()["events"]] == ["created"]


@pytest.mark.parametrize("status", [CreativePlanStatus.DRAFT, CreativePlanStatus.ARCHIVED])
def test_unselected_plan_cannot_create_job(
    client, db_session, auth_headers_factory, status
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE, status)
    response = _create_job(
        client,
        product,
        plan,
        auth_headers_factory(UserRole.ADMIN),
        GenerationJobKind.IMAGE,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "creative_plan_not_selected"


@pytest.mark.parametrize(
    ("plan_type", "requested_kind"),
    [
        (CreativePlanType.MAIN_IMAGE, GenerationJobKind.VIDEO),
        (CreativePlanType.VIDEO_SCRIPT, GenerationJobKind.IMAGE),
    ],
)
def test_plan_type_and_job_kind_cannot_be_crossed(
    client, db_session, auth_headers_factory, plan_type, requested_kind
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, plan_type)
    response = _create_job(
        client,
        product,
        plan,
        auth_headers_factory(UserRole.ADMIN),
        requested_kind,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "creative_plan_job_kind_mismatch"


def test_viewer_and_cross_product_cannot_create_job(
    client, db_session, auth_headers_factory
):
    product_a = _create_product(db_session, "a")
    product_b = _create_product(db_session, "b")
    plan = _create_plan(db_session, product_a, CreativePlanType.MAIN_IMAGE)
    viewer = auth_headers_factory(UserRole.VIEWER)
    assert _create_job(
        client, product_a, plan, viewer, GenerationJobKind.IMAGE
    ).status_code == 403
    response = _create_job(
        client,
        product_b,
        plan,
        auth_headers_factory(UserRole.ADMIN),
        GenerationJobKind.IMAGE,
    )
    assert response.status_code == 404


def test_run_commits_running_before_generator_then_succeeds(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    headers = auth_headers_factory(UserRole.OPERATOR)
    job_id = _create_job(
        client, product, plan, headers, GenerationJobKind.IMAGE
    ).json()["id"]
    commit_count = [0]

    def count_commit(_: Session) -> None:
        commit_count[0] += 1

    event.listen(db_session, "after_commit", count_commit)
    generator = ObservingImageGenerator(db_session, commit_count)
    app.dependency_overrides[get_image_generator] = lambda: generator
    try:
        response = client.post(
            f"/api/v1/products/{product.id}/generation-jobs/{job_id}/run",
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_image_generator, None)
        event.remove(db_session, "after_commit", count_commit)

    assert response.status_code == 200
    body = response.json()
    assert generator.saw_running is True
    assert generator.saw_started_event is True
    assert commit_count[0] == 2
    assert body["job_status"] == "succeeded"
    assert body["attempts"] == 1
    assert body["started_at"] is not None
    assert body["finished_at"] is not None
    assert body["locked_at"] is None
    assert body["result_json"]["asset_type"] == "image"
    assert body["result_json"]["url"] == f"mock://images/job-{job_id}.png"
    assert [item["event_type"] for item in body["events"]] == [
        "created",
        "started",
        "succeeded",
    ]


def test_mock_video_run_has_deterministic_structure(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.VIDEO_SCRIPT)
    headers = auth_headers_factory(UserRole.ADMIN)
    job_id = _create_job(
        client, product, plan, headers, GenerationJobKind.VIDEO
    ).json()["id"]
    response = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job_id}/run",
        headers=headers,
    )
    assert response.status_code == 200
    result = response.json()["result_json"]
    assert result == {
        "asset_type": "video",
        "mock": True,
        "url": f"mock://videos/job-{job_id}.mp4",
        "duration_sec": 15,
        "generator": "mock_video_generator",
    }


def test_generator_failure_sets_failed_without_success_result(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    headers = auth_headers_factory(UserRole.OPERATOR)
    job_id = _create_job(
        client, product, plan, headers, GenerationJobKind.IMAGE
    ).json()["id"]
    app.dependency_overrides[get_image_generator] = lambda: FailingGenerator()
    try:
        response = client.post(
            f"/api/v1/products/{product.id}/generation-jobs/{job_id}/run",
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_image_generator, None)
    assert response.status_code == 200
    body = response.json()
    assert body["job_status"] == "failed"
    assert body["result_json"] is None
    assert body["error_message"] == "deterministic generator failure"
    assert [item["event_type"] for item in body["events"]][-1] == "failed"


def test_retry_keeps_attempts_and_full_timeline_then_succeeds(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    headers = auth_headers_factory(UserRole.ADMIN)
    job_id = _create_job(
        client, product, plan, headers, GenerationJobKind.IMAGE
    ).json()["id"]
    app.dependency_overrides[get_image_generator] = lambda: FailingGenerator()
    failed = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job_id}/run",
        headers=headers,
    )
    app.dependency_overrides.pop(get_image_generator, None)
    assert failed.json()["attempts"] == 1

    retried = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job_id}/retry",
        headers=headers,
    )
    assert retried.status_code == 200
    assert retried.json()["job_status"] == "pending"
    assert retried.json()["attempts"] == 1
    assert retried.json()["error_message"] is None

    succeeded = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job_id}/run",
        headers=headers,
    )
    assert succeeded.json()["attempts"] == 2
    assert [item["event_type"] for item in succeeded.json()["events"]] == [
        "created",
        "started",
        "failed",
        "retry_requested",
        "started",
        "succeeded",
    ]


@pytest.mark.parametrize(
    "status", [GenerationJobStatus.SUCCEEDED, GenerationJobStatus.CANCELLED]
)
def test_succeeded_or_cancelled_job_cannot_retry(
    client, db_session, auth_headers_factory, status
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=status,
    )
    db_session.add(job)
    db_session.commit()
    response = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job.id}/retry",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    assert response.status_code == 409


def test_attempt_limit_blocks_retry_and_run(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    headers = auth_headers_factory(UserRole.ADMIN)
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.FAILED,
        attempts=3,
        max_attempts=3,
    )
    db_session.add(job)
    db_session.commit()
    retry = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job.id}/retry",
        headers=headers,
    )
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "generation_job_attempt_limit_reached"
    job.job_status = GenerationJobStatus.PENDING
    db_session.commit()
    run = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job.id}/run",
        headers=headers,
    )
    assert run.status_code == 409


def test_pending_can_cancel_but_running_and_succeeded_cannot(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    operator = auth_headers_factory(UserRole.OPERATOR)
    pending_id = _create_job(
        client, product, plan, operator, GenerationJobKind.IMAGE
    ).json()["id"]
    cancelled = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{pending_id}/cancel",
        headers=operator,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["job_status"] == "cancelled"
    assert cancelled.json()["events"][-1]["event_type"] == "cancelled"

    for status in (GenerationJobStatus.RUNNING, GenerationJobStatus.SUCCEEDED):
        job = GenerationJob(
            product_id=product.id,
            creative_plan_id=plan.id,
            job_kind=GenerationJobKind.IMAGE,
            job_status=status,
        )
        db_session.add(job)
        db_session.commit()
        response = client.post(
            f"/api/v1/products/{product.id}/generation-jobs/{job.id}/cancel",
            headers=operator,
        )
        assert response.status_code == 409
        if status == GenerationJobStatus.RUNNING:
            assert response.json()["error"]["code"] == (
                "running_job_cancellation_not_supported"
            )


def test_viewer_cannot_run_retry_or_cancel_but_can_query(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    admin = auth_headers_factory(UserRole.ADMIN)
    viewer = auth_headers_factory(UserRole.VIEWER)
    job_id = _create_job(
        client, product, plan, admin, GenerationJobKind.IMAGE
    ).json()["id"]
    assert client.get(
        f"/api/v1/products/{product.id}/generation-jobs/{job_id}",
        headers=viewer,
    ).status_code == 200
    for action in ("run", "retry", "cancel"):
        assert client.post(
            f"/api/v1/products/{product.id}/generation-jobs/{job_id}/{action}",
            headers=viewer,
        ).status_code == 403


def test_timeout_sweep_only_changes_expired_running_and_admin_only(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    old = datetime.now(timezone.utc) - timedelta(seconds=301)
    recent = datetime.now(timezone.utc) - timedelta(seconds=30)
    expired = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.RUNNING,
        attempts=1,
        started_at=old,
        locked_at=old,
        locked_by="manual-runner:test",
    )
    not_expired = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.RUNNING,
        attempts=1,
        started_at=recent,
        locked_at=recent,
        locked_by="manual-runner:test",
    )
    pending = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.PENDING,
    )
    db_session.add_all([expired, not_expired, pending])
    db_session.commit()

    path = "/api/v1/workspace/generation-jobs/sweep-timeouts"
    assert client.post(
        path, headers=auth_headers_factory(UserRole.OPERATOR)
    ).status_code == 403
    assert client.post(
        path, headers=auth_headers_factory(UserRole.VIEWER)
    ).status_code == 403
    response = client.post(path, headers=auth_headers_factory(UserRole.ADMIN))
    assert response.status_code == 200
    assert response.json() == {"timed_out_count": 1, "job_ids": [expired.id]}
    db_session.refresh(expired)
    db_session.refresh(not_expired)
    db_session.refresh(pending)
    assert expired.job_status == GenerationJobStatus.TIMEOUT
    assert expired.finished_at is not None
    assert not_expired.job_status == GenerationJobStatus.RUNNING
    assert pending.job_status == GenerationJobStatus.PENDING
    events = GenerationJobEventRepository(db_session).list_by_job(expired.id)
    assert [item.event_type for item in events] == [GenerationJobEventType.TIMEOUT]


def test_timeout_job_can_retry_without_resetting_attempts(
    client, db_session, auth_headers_factory
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    job = GenerationJob(
        product_id=product.id,
        creative_plan_id=plan.id,
        job_kind=GenerationJobKind.IMAGE,
        job_status=GenerationJobStatus.TIMEOUT,
        attempts=1,
        max_attempts=3,
        error_message="previous timeout",
    )
    db_session.add(job)
    db_session.commit()
    response = client.post(
        f"/api/v1/products/{product.id}/generation-jobs/{job.id}/retry",
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 200
    assert response.json()["job_status"] == "pending"
    assert response.json()["attempts"] == 1


def test_list_filters_and_latest_order(client, db_session, auth_headers_factory):
    product = _create_product(db_session)
    image_plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    video_plan = _create_plan(db_session, product, CreativePlanType.VIDEO_SCRIPT)
    headers = auth_headers_factory(UserRole.ADMIN)
    image_id = _create_job(
        client, product, image_plan, headers, GenerationJobKind.IMAGE
    ).json()["id"]
    video_id = _create_job(
        client, product, video_plan, headers, GenerationJobKind.VIDEO
    ).json()["id"]
    response = client.get(
        f"/api/v1/products/{product.id}/generation-jobs?job_kind=image&job_status=pending",
        headers=headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [image_id]
    all_jobs = client.get(
        f"/api/v1/products/{product.id}/generation-jobs?page=1&page_size=1",
        headers=headers,
    ).json()
    assert all_jobs["total"] == 2
    assert all_jobs["items"][0]["id"] == video_id


def test_job_and_product_not_found(client, db_session, auth_headers_factory):
    product = _create_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    assert client.get(
        f"/api/v1/products/{product.id}/generation-jobs/9999", headers=headers
    ).status_code == 404
    assert client.get(
        "/api/v1/products/9999/generation-jobs", headers=headers
    ).status_code == 404


def test_created_job_and_event_roll_back_together(db_session, monkeypatch):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)

    def fail_add(*_: object) -> None:
        raise RuntimeError("event insert failure")

    monkeypatch.setattr(GenerationJobEventRepository, "add", fail_add)
    with pytest.raises(RuntimeError, match="event insert failure"):
        GenerationJobService(db_session).create_image_job(product.id, plan.id)
    assert db_session.scalar(select(func.count()).select_from(GenerationJob)) == 0
    assert db_session.scalar(select(func.count()).select_from(GenerationJobEvent)) == 0


@pytest.mark.parametrize("failure_event", ["succeeded", "failed"])
def test_terminal_status_and_event_roll_back_together(
    db_session, monkeypatch, failure_event
):
    product = _create_product(db_session)
    plan = _create_plan(db_session, product, CreativePlanType.MAIN_IMAGE)
    service = GenerationJobService(db_session)
    job = service.create_image_job(product.id, plan.id)
    original_add = GenerationJobEventRepository.add

    def selectively_fail(repository, event_record):
        if event_record.event_type.value == failure_event:
            raise RuntimeError("terminal event insert failure")
        return original_add(repository, event_record)

    monkeypatch.setattr(GenerationJobEventRepository, "add", selectively_fail)
    generator = FailingGenerator() if failure_event == "failed" else MockImageGenerator()
    with pytest.raises(RuntimeError, match="terminal event insert failure"):
        service.run(
            product_id=product.id,
            job_id=job.id,
            locked_by="manual-runner:test",
            image_generator=generator,
            video_generator=generator,
        )
    db_session.expire_all()
    stored = db_session.get(GenerationJob, job.id)
    assert stored is not None
    assert stored.job_status == GenerationJobStatus.RUNNING
    assert stored.result_json is None
    event_types = [
        item.event_type
        for item in GenerationJobEventRepository(db_session).list_by_job(job.id)
    ]
    assert event_types == [
        GenerationJobEventType.CREATED,
        GenerationJobEventType.STARTED,
    ]
