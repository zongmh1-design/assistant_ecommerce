"""PostgreSQL-only acceptance checks.

These tests skip during the normal SQLite suite. Run them only against a
migrated, disposable local database containing Phase 13 demo data.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import AppError
from app.generation.mock_generators import MockImageGenerator, MockVideoGenerator
from app.models.creative_plan import CreativePlanStatus
from app.models.generation_job import GenerationJobEvent, GenerationJobEventType
from app.repositories.ad_experiment_repository import AdExperimentRepository
from app.repositories.ad_recommendation_repository import AdRecommendationRepository
from app.schemas.creative_plan import CreativePlanUpdate
from app.schemas.performance_record import PerformanceRecordCreate
from app.services.creative_plan_service import CreativePlanService
from app.services.generation_job_service import GenerationJobService
from app.services.performance_record_service import PerformanceRecordService
from scripts.smoke_test_demo_flow import StdlibClient


POSTGRES_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")
API_BASE_URL = os.getenv("TEST_API_BASE_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="TEST_POSTGRES_DATABASE_URL is not configured",
)

REQUIRED_TABLES = {
    "users",
    "stores",
    "products",
    "product_skus",
    "inventory_items",
    "inventory_movements",
    "competitors",
    "product_diagnoses",
    "creative_plans",
    "generation_jobs",
    "generation_job_events",
    "generated_assets",
    "promotion_links",
    "promotion_link_clicks",
    "ad_recommendations",
    "ad_experiments",
    "performance_records",
    "review_reports",
}


@pytest.fixture(scope="module")
def engine():
    assert POSTGRES_URL is not None
    value = create_engine(POSTGRES_URL, pool_pre_ping=True)
    try:
        assert value.dialect.name == "postgresql"
        yield value
    finally:
        value.dispose()


@pytest.fixture(scope="module")
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_catalog_contains_tables_constraints_and_partial_index(engine) -> None:
    inspector = inspect(engine)
    assert REQUIRED_TABLES <= set(inspector.get_table_names())

    creative_indexes = {
        item["name"]: item for item in inspector.get_indexes("creative_plans")
    }
    selected = creative_indexes["uq_creative_plans_selected_product_type"]
    assert selected["unique"] is True
    predicate = str(
        selected.get("dialect_options", {}).get("postgresql_where", "")
    )
    assert "selected" in predicate

    asset_uniques = {
        item["name"] for item in inspector.get_unique_constraints("generated_assets")
    }
    assert "uq_generated_assets_generation_job_id" in asset_uniques
    assert "uq_generated_assets_plan_type_version" in asset_uniques

    link_indexes = {
        item["name"]: item for item in inspector.get_indexes("promotion_links")
    }
    assert link_indexes["uq_promotion_links_tracking_code"]["unique"] is True

    performance_checks = {
        item["name"] for item in inspector.get_check_constraints("performance_records")
    }
    assert {
        "ck_performance_records_period_order",
        "ck_performance_records_clicks_within_impressions",
        "ck_performance_records_conversions_within_clicks",
        "ck_performance_records_ctr_range",
        "ck_performance_records_conversion_rate_range",
    } <= performance_checks


def test_demo_numeric_json_and_for_update_queries(engine, session_factory) -> None:
    with session_factory() as session:
        product_id, experiment_id = session.execute(
            text(
                "SELECT product_id, id FROM ad_experiments "
                "WHERE experiment_status = 'finished' ORDER BY id DESC LIMIT 1"
            )
        ).one()
        record = PerformanceRecordService(session).create(
            product_id,
            PerformanceRecordCreate(
                experiment_id=experiment_id,
                period_start=datetime(2026, 9, 5, tzinfo=timezone.utc),
                period_end=datetime(2026, 9, 6, tzinfo=timezone.utc),
                impressions=1000,
                clicks=50,
                conversions=5,
                spend=Decimal("100.00"),
                revenue=Decimal("150.00"),
                notes="Phase 14 PostgreSQL NUMERIC acceptance data",
            ),
        )
        record_id = record.id

    with engine.connect() as connection:
        numeric = connection.execute(
            text(
                "SELECT ctr, conversion_rate, roi FROM performance_records "
                "WHERE id = :record_id"
            ),
            {"record_id": record_id},
        ).mappings().one()
        assert numeric["ctr"] == Decimal("0.050000")
        assert numeric["conversion_rate"] == Decimal("0.100000")
        assert numeric["roi"] == Decimal("0.500000")
        context = connection.execute(
            text(
                "SELECT input_context_json FROM review_reports "
                "ORDER BY id DESC LIMIT 1"
            )
        ).scalar_one()
        assert isinstance(context, dict)
        assert "aggregated_performance" in context

    with session_factory() as session:
        product_id, recommendation_id = session.execute(
            text(
                "SELECT product_id, id FROM ad_recommendations "
                "WHERE confirm_status = 'confirmed' ORDER BY id DESC LIMIT 1"
            )
        ).one()
        experiment_id = session.execute(
            text(
                "SELECT id FROM ad_experiments WHERE product_id = :product_id "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"product_id": product_id},
        ).scalar_one()
        assert (
            AdRecommendationRepository(
                session
            ).get_for_update_by_id_and_product_id(
                recommendation_id, product_id
            )
            is not None
        )
        assert (
            AdExperimentRepository(session).get_for_update_by_id_and_product_id(
                experiment_id, product_id
            )
            is not None
        )
        session.rollback()


def test_creative_selected_partial_unique_and_service_switch(session_factory) -> None:
    with session_factory() as session:
        product_id = session.execute(
            text(
                "SELECT id FROM products WHERE name LIKE '%[Demo Mock]' "
                "ORDER BY id LIMIT 1"
            )
        ).scalar_one()
        original_selected_id = session.execute(
            text(
                "SELECT id FROM creative_plans WHERE product_id = :product_id "
                "AND plan_type = 'main_image' AND status = 'selected'"
            ),
            {"product_id": product_id},
        ).scalar_one()
        draft_id = session.execute(
            text(
                "SELECT id FROM creative_plans WHERE product_id = :product_id "
                "AND plan_type = 'main_image' AND status = 'draft' "
                "ORDER BY id LIMIT 1"
            ),
            {"product_id": product_id},
        ).scalar_one()
        CreativePlanService(session).update(
            product_id,
            draft_id,
            CreativePlanUpdate(status=CreativePlanStatus.SELECTED),
        )
        selected_count = session.execute(
            text(
                "SELECT count(*) FROM creative_plans WHERE product_id = :product_id "
                "AND plan_type = 'main_image' AND status = 'selected'"
            ),
            {"product_id": product_id},
        ).scalar_one()
        assert selected_count == 1
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "UPDATE creative_plans SET status = 'selected' "
                    "WHERE id = :plan_id"
                ),
                {"plan_id": original_selected_id},
            )
        session.rollback()

        # Keep this acceptance test repeatable and preserve the Demo selection.
        session.execute(
            text("UPDATE creative_plans SET status = 'draft' WHERE id = :plan_id"),
            {"plan_id": draft_id},
        )
        session.execute(
            text(
                "UPDATE creative_plans SET status = 'selected' "
                "WHERE id = :plan_id"
            ),
            {"plan_id": original_selected_id},
        )
        session.commit()


def test_generation_job_is_claimed_once_with_postgres_row_lock(
    session_factory,
) -> None:
    with session_factory() as setup:
        product_id, plan_id = setup.execute(
            text(
                "SELECT product_id, id FROM creative_plans "
                "WHERE plan_type = 'main_image' AND status = 'selected' "
                "ORDER BY id DESC LIMIT 1"
            )
        ).one()
        job = GenerationJobService(setup).create_image_job(product_id, plan_id)
        job_id = job.id

    def run_once(worker: str) -> str:
        with session_factory() as session:
            try:
                result = GenerationJobService(session).run(
                    product_id=product_id,
                    job_id=job_id,
                    locked_by=worker,
                    image_generator=MockImageGenerator(),
                    video_generator=MockVideoGenerator(),
                )
                return result.job_status.value
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(run_once, ("pg-worker-1", "pg-worker-2"))
        )
    assert outcomes.count("succeeded") == 1
    assert len(outcomes) == 2

    with session_factory() as verification:
        attempts = verification.execute(
            text("SELECT attempts FROM generation_jobs WHERE id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
        started = (
            verification.query(GenerationJobEvent)
            .filter(
                GenerationJobEvent.job_id == job_id,
                GenerationJobEvent.event_type == GenerationJobEventType.STARTED,
            )
            .count()
        )
        assert attempts == 1
        assert started == 1


def test_generated_asset_version_unique_rejects_real_duplicate(engine) -> None:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        asset_id, source_job_id = connection.execute(
            text(
                "SELECT id, generation_job_id FROM generated_assets "
                "ORDER BY id LIMIT 1"
            )
        ).one()
        replacement_job_id = connection.execute(
            text(
                "INSERT INTO generation_jobs "
                "(product_id, creative_plan_id, job_kind, job_status, "
                "attempts, max_attempts) "
                "SELECT product_id, creative_plan_id, job_kind, 'succeeded', 1, 3 "
                "FROM generation_jobs WHERE id = :source_job_id RETURNING id"
            ),
            {"source_job_id": source_job_id},
        ).scalar_one()
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO generated_assets "
                    "(product_id, creative_plan_id, generation_job_id, asset_type, "
                    "asset_url, model_name, width, height, duration_sec, "
                    "review_status, version_no, usage_scene, score, tags_json, remark) "
                    "SELECT product_id, creative_plan_id, :replacement_job_id, "
                    "asset_type, asset_url, model_name, width, height, duration_sec, "
                    "review_status, version_no, usage_scene, score, tags_json, remark "
                    "FROM generated_assets WHERE id = :asset_id"
                ),
                {
                    "replacement_job_id": replacement_job_id,
                    "asset_id": asset_id,
                },
            )
    finally:
        transaction.rollback()
        connection.close()


@pytest.mark.skipif(
    not API_BASE_URL,
    reason="TEST_API_BASE_URL is not configured",
)
def test_public_redirect_uses_atomic_click_counter(engine) -> None:
    with engine.connect() as connection:
        link_id, tracking_code, before_count = connection.execute(
            text(
                "SELECT id, tracking_code, click_count FROM promotion_links "
                "WHERE status = 'active' ORDER BY id DESC LIMIT 1"
            )
        ).one()
        before_rows = connection.execute(
            text(
                "SELECT count(*) FROM promotion_link_clicks "
                "WHERE promotion_link_id = :link_id"
            ),
            {"link_id": link_id},
        ).scalar_one()

    def click(_: int) -> int:
        assert API_BASE_URL is not None
        with StdlibClient(API_BASE_URL, timeout=10) as client:
            return client.get(
                f"/api/v1/r/{tracking_code}"
            ).status_code

    click_total = 12
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(click, range(click_total)))
    assert statuses == [302] * click_total

    with engine.connect() as connection:
        after_count = connection.execute(
            text(
                "SELECT click_count FROM promotion_links WHERE id = :link_id"
            ),
            {"link_id": link_id},
        ).scalar_one()
        after_rows = connection.execute(
            text(
                "SELECT count(*) FROM promotion_link_clicks "
                "WHERE promotion_link_id = :link_id"
            ),
            {"link_id": link_id},
        ).scalar_one()
    assert after_count - before_count == click_total
    assert after_rows - before_rows == click_total
