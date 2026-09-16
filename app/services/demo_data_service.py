"""Resumable demo composition that only writes through existing business services."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.mock_llm_provider import MockLLMProvider
from app.core.exceptions import AppError
from app.generation.mock_generators import MockImageGenerator, MockVideoGenerator
from app.models.ad_experiment import AdExperiment, AdExperimentStatus
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.competitor import Competitor
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset, GeneratedAssetType
from app.models.generation_job import GenerationJob, GenerationJobKind, GenerationJobStatus
from app.models.performance_record import PerformanceRecord
from app.models.product import Product, ProductStatus
from app.models.product_diagnosis import ProductDiagnosis
from app.models.product_sku import ProductSku
from app.models.promotion_link import PromotionLink
from app.models.review_report import ReviewReport
from app.models.store import Platform, Store
from app.schemas.ad_experiment import AdExperimentGenerate, AdExperimentStatusUpdate
from app.schemas.ad_recommendation import AdRecommendationConfirmation
from app.schemas.competitor import CompetitorCreate
from app.schemas.creative_plan import CreativePlanUpdate
from app.schemas.demo_data import DemoDataResponse
from app.schemas.generated_asset import GeneratedAssetUpdate
from app.schemas.inventory import InventoryAdjustment, InventorySettingsUpdate
from app.schemas.performance_record import PerformanceRecordCreate
from app.schemas.product import ProductCreate
from app.schemas.product_sku import ProductSkuCreate
from app.schemas.promotion_link import PromotionLinkCreate, PromotionUtm
from app.schemas.review_report import ReviewReportGenerate
from app.schemas.store import StoreCreate
from app.services.ad_experiment_service import AdExperimentService
from app.services.ad_recommendation_service import AdRecommendationService
from app.services.competitor_service import CompetitorService
from app.services.creative_plan_service import CreativePlanService
from app.services.generated_asset_service import GeneratedAssetService
from app.services.generation_job_service import GenerationJobService
from app.services.inventory_service import InventoryService
from app.services.performance_record_service import PerformanceRecordService
from app.services.product_diagnosis_service import ProductDiagnosisService
from app.services.product_service import ProductService
from app.services.product_sku_service import ProductSkuService
from app.services.promotion_link_service import PromotionLinkService
from app.services.review_report_service import ReviewReportService
from app.services.store_service import StoreService


DEMO_STORE_NAME = "Demo 数码店 [Demo]"
DEMO_PRODUCT_NAME = "轻量磁吸移动电源 [Demo Mock]"
DEMO_LINK_NAME = "Demo 社交媒体推广链接 [Mock]"
DEMO_PERIOD_START = datetime.fromisoformat("2026-09-01T00:00:00+00:00")
DEMO_PERIOD_END = datetime.fromisoformat("2026-09-04T00:00:00+00:00")


class DemoDataService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.provider = MockLLMProvider()
        self.completed_steps: list[str] = []
        self.ids: dict[str, Any] = {"sku_ids": [], "performance_record_ids": []}
        self.created_any = False
        self.current_step = "store"

    def initialize(self, admin_user_id: int) -> DemoDataResponse:
        root_existed = self._find_store() is not None
        try:
            store = self._ensure_store()
            product = self._ensure_product(store)
            skus = self._ensure_skus_and_inventory(product)
            competitors = self._ensure_competitors(product)
            diagnosis = self._ensure_diagnosis(product)
            main_plan, video_plan = self._ensure_creative_plans(product)
            image_job, video_job = self._ensure_jobs(product, main_plan, video_plan)
            image_asset, video_asset = self._ensure_assets(product, image_job, video_job)
            link = self._ensure_promotion_link(product)
            recommendation = self._ensure_recommendation(product, admin_user_id)
            experiment = self._ensure_experiment(
                product, recommendation, image_asset, link
            )
            records = self._ensure_performance_records(product, experiment)
            report = self._ensure_review_report(product)
            self._validate_consistency(
                product, skus, competitors, diagnosis, main_plan, video_plan,
                image_job, video_job, image_asset, video_asset, link,
                recommendation, experiment, records, report,
            )
            self._done("consistency_check")
        except AppError as exc:
            return self._response(
                status="partial", failed_step=self.current_step, error_code=exc.code
            )
        except Exception:
            self.db.rollback()
            return self._response(
                status="partial", failed_step=self.current_step,
                error_code="demo_initialization_failed",
            )
        status = "already_exists" if root_existed and not self.created_any else "completed"
        return self._response(status=status)

    def _ensure_store(self) -> Store:
        self.current_step = "store"
        store = self._find_store()
        if store is None:
            store = StoreService(self.db).create(StoreCreate(
                store_name=DEMO_STORE_NAME,
                platform=Platform.JD,
                external_store_id="demo-store-mock",
                owner_name="Demo Operator",
                remark="Demo/Mock 数据；不代表真实京东店铺或平台授权。",
            ))
            self.created_any = True
        self.ids["store_id"] = store.id
        self._done("store")
        return store

    def _ensure_product(self, store: Store) -> Product:
        self.current_step = "product"
        product = self.db.scalar(select(Product).where(
            Product.store_id == store.id, Product.name == DEMO_PRODUCT_NAME
        ))
        if product is None:
            product = ProductService(self.db).create(ProductCreate(
                store_id=store.id, name=DEMO_PRODUCT_NAME, platform=Platform.JD,
                category="数码配件", price=Decimal("159.00"), cost=Decimal("78.00"),
                target_audience="需要轻量便携充电方案的通勤和旅行用户",
                selling_points=["轻量便携", "磁吸使用", "双容量规格", "Demo Mock 数据"],
                product_url="https://example.com/demo-power-bank",
                images_json=["mock://demo/product-cover.png"],
                status=ProductStatus.ACTIVE,
            ))
            self.created_any = True
        self.ids["product_id"] = product.id
        self._done("product")
        return product

    def _ensure_skus_and_inventory(self, product: Product) -> list[ProductSku]:
        self.current_step = "sku_inventory"
        definitions = (
            ("DEMO-PB-5000", "5000mAh Demo", "5000mAh", "129.00", "62.00", 80, 15),
            ("DEMO-PB-10000", "10000mAh Demo", "10000mAh", "189.00", "92.00", 50, 10),
        )
        skus: list[ProductSku] = []
        sku_service = ProductSkuService(self.db)
        inventory_service = InventoryService(self.db)
        for code, name, capacity, price, cost, target_stock, warning in definitions:
            sku = self.db.scalar(select(ProductSku).where(
                ProductSku.product_id == product.id, ProductSku.sku_code == code
            ))
            if sku is None:
                sku = sku_service.create(product.id, ProductSkuCreate(
                    sku_code=code, sku_name=name,
                    spec_json={"capacity": capacity, "data_source": "Demo Mock"},
                    price=Decimal(price), cost=Decimal(cost),
                    platform_sku_id=f"mock-{code.lower()}",
                ))
                self.created_any = True
            inventory = inventory_service.get(sku.id)
            if inventory.stock_qty < target_stock:
                inventory_service.adjust(sku.id, InventoryAdjustment(
                    change_qty=target_stock - inventory.stock_qty,
                    reason_text="Demo Mock 采购入库",
                    reference_type="demo_initializer",
                    reference_id="phase-13",
                ))
                self.created_any = True
            if inventory.warning_threshold != warning or inventory.location_text != "Demo 仓位 A":
                inventory_service.update_settings(sku.id, InventorySettingsUpdate(
                    warning_threshold=warning, location_text="Demo 仓位 A"
                ))
            skus.append(sku)
        self.ids["sku_ids"] = [sku.id for sku in skus]
        self._done("sku_inventory")
        return skus

    def _ensure_competitors(self, product: Product) -> list[Competitor]:
        self.current_step = "competitors"
        definitions = (
            ("Demo 竞品 A [Mock]", "https://example.com/demo-competitor-a", "149.00", ["便携", "磁吸"]),
            ("Demo 竞品 B [Mock]", "https://example.com/demo-competitor-b", "199.00", ["容量", "快充"]),
        )
        service = CompetitorService(self.db)
        competitors = []
        for name, url, price, points in definitions:
            competitor = self.db.scalar(select(Competitor).where(
                Competitor.product_id == product.id, Competitor.name == name
            ))
            if competitor is None:
                competitor = service.create(product.id, CompetitorCreate(
                    name=name, platform=Platform.OTHER, url=url,
                    price=Decimal(price), title=f"{name} 示例标题",
                    sales_hint="Demo 示例数据，不代表真实销量",
                    selling_points=points, review_keywords=["Demo", "Mock"],
                ))
                self.created_any = True
            competitors.append(competitor)
        self._done("competitors")
        return competitors

    def _ensure_diagnosis(self, product: Product) -> ProductDiagnosis:
        self.current_step = "diagnosis"
        diagnosis = self.db.scalar(select(ProductDiagnosis).where(
            ProductDiagnosis.product_id == product.id
        ).order_by(ProductDiagnosis.id.desc()).limit(1))
        if diagnosis is None:
            diagnosis = ProductDiagnosisService(self.db).generate(product.id, self.provider)
            self.created_any = True
        self._done("diagnosis")
        return diagnosis

    def _ensure_creative_plans(self, product: Product) -> tuple[CreativePlan, CreativePlan]:
        self.current_step = "creative_plans"
        service = CreativePlanService(self.db)
        all_plans = list(self.db.scalars(select(CreativePlan).where(
            CreativePlan.product_id == product.id
        ).order_by(CreativePlan.id)))
        if not any(plan.plan_type == CreativePlanType.MAIN_IMAGE for plan in all_plans):
            all_plans.extend(service.generate_main_images(product.id, self.provider))
            self.created_any = True
        if not any(plan.plan_type == CreativePlanType.VIDEO_SCRIPT for plan in all_plans):
            all_plans.extend(service.generate_video_scripts(product.id, self.provider))
            self.created_any = True
        main_plan = self._select_plan(service, product.id, all_plans, CreativePlanType.MAIN_IMAGE)
        video_plan = self._select_plan(service, product.id, all_plans, CreativePlanType.VIDEO_SCRIPT)
        self.ids["selected_main_image_plan_id"] = main_plan.id
        self.ids["selected_video_plan_id"] = video_plan.id
        self._done("creative_plans")
        return main_plan, video_plan

    def _select_plan(
        self, service: CreativePlanService, product_id: int,
        plans: list[CreativePlan], plan_type: CreativePlanType,
    ) -> CreativePlan:
        selected = next((p for p in plans if p.plan_type == plan_type and p.status == CreativePlanStatus.SELECTED), None)
        if selected is not None:
            return selected
        draft = next(p for p in plans if p.plan_type == plan_type and p.status == CreativePlanStatus.DRAFT)
        self.created_any = True
        return service.update(product_id, draft.id, CreativePlanUpdate(status=CreativePlanStatus.SELECTED))

    def _ensure_jobs(
        self, product: Product, main_plan: CreativePlan, video_plan: CreativePlan
    ) -> tuple[GenerationJob, GenerationJob]:
        self.current_step = "generation_jobs"
        service = GenerationJobService(self.db)
        image_job = self._ensure_job(service, product.id, main_plan.id, GenerationJobKind.IMAGE)
        video_job = self._ensure_job(service, product.id, video_plan.id, GenerationJobKind.VIDEO)
        self.ids["image_job_id"] = image_job.id
        self.ids["video_job_id"] = video_job.id
        self._done("generation_jobs")
        return image_job, video_job

    def _ensure_job(
        self, service: GenerationJobService, product_id: int,
        plan_id: int, kind: GenerationJobKind,
    ) -> GenerationJob:
        job = self.db.scalar(select(GenerationJob).where(
            GenerationJob.product_id == product_id,
            GenerationJob.creative_plan_id == plan_id,
            GenerationJob.job_kind == kind,
        ).order_by(GenerationJob.id).limit(1))
        if job is None:
            job = (
                service.create_image_job(product_id, plan_id)
                if kind == GenerationJobKind.IMAGE
                else service.create_video_job(product_id, plan_id)
            )
            self.created_any = True
        if job.job_status in {GenerationJobStatus.FAILED, GenerationJobStatus.TIMEOUT}:
            job = service.retry(product_id, job.id)
        if job.job_status == GenerationJobStatus.PENDING:
            job = service.run(
                product_id=product_id, job_id=job.id, locked_by="demo-initializer",
                image_generator=MockImageGenerator(), video_generator=MockVideoGenerator(),
            )
            self.created_any = True
        if job.job_status != GenerationJobStatus.SUCCEEDED:
            raise AppError(
                status_code=409, code="demo_generation_job_not_succeeded",
                message=f"Demo generation job {job.id} is not succeeded",
            )
        return job

    def _ensure_assets(
        self, product: Product, image_job: GenerationJob, video_job: GenerationJob
    ) -> tuple[GeneratedAsset, GeneratedAsset]:
        self.current_step = "assets"
        service = GeneratedAssetService(self.db)
        if self._asset_for_job(image_job.id) is None or self._asset_for_job(video_job.id) is None:
            result = service.sync_succeeded_jobs(product.id)
            if result.failed_count:
                raise AppError(
                    status_code=409, code="demo_asset_sync_failed",
                    message="One or more demo jobs failed asset synchronization",
                )
            self.created_any = self.created_any or result.synced_count > 0
        image_asset = self._asset_for_job(image_job.id)
        video_asset = self._asset_for_job(video_job.id)
        if image_asset is None or video_asset is None:
            raise AppError(
                status_code=409, code="demo_asset_missing",
                message="Demo assets were not created",
            )
        image_asset = self._approve_asset(service, product.id, image_asset, "Demo 主图", ["Demo", "Mock", "主图"])
        video_asset = self._approve_asset(service, product.id, video_asset, "Demo 短视频", ["Demo", "Mock", "视频"])
        self.ids["approved_image_asset_id"] = image_asset.id
        self.ids["approved_video_asset_id"] = video_asset.id
        self._done("assets")
        return image_asset, video_asset

    def _approve_asset(
        self, service: GeneratedAssetService, product_id: int,
        asset: GeneratedAsset, scene: str, tags: list[str],
    ) -> GeneratedAsset:
        if asset.review_status == AssetReviewStatus.APPROVED:
            return asset
        self.created_any = True
        return service.update(product_id, asset.id, GeneratedAssetUpdate(
            review_status=AssetReviewStatus.APPROVED,
            usage_scene=scene, score=85, tags_json=tags,
            remark="Demo Mock 素材审核通过",
        ))

    def _ensure_promotion_link(self, product: Product) -> PromotionLink:
        self.current_step = "promotion_link"
        service = PromotionLinkService(self.db)
        link = self.db.scalar(select(PromotionLink).where(
            PromotionLink.product_id == product.id,
            PromotionLink.link_name == DEMO_LINK_NAME,
        ))
        if link is None:
            suggestion = service.generate_suggestion(product.id, self.provider)
            link = service.create(product.id, PromotionLinkCreate(
                link_name=DEMO_LINK_NAME,
                target_url="https://example.com/demo-power-bank",
                utm_json=PromotionUtm(
                    utm_source=suggestion.utm_source,
                    utm_medium=suggestion.utm_medium,
                    utm_campaign="demo_mock_campaign",
                    utm_content=suggestion.utm_content,
                ),
                scene_text=f"{suggestion.scene_text}（Demo Mock）",
            ))
            self.created_any = True
        while link.click_count < 3:
            service.record_click(
                link.tracking_code, client_ip=None,
                user_agent="DemoDataInitializer/1.0 (Mock)",
            )
            self.db.refresh(link)
            self.created_any = True
        self.ids["promotion_link_id"] = link.id
        self._done("promotion_link")
        return link

    def _ensure_recommendation(
        self, product: Product, admin_user_id: int
    ) -> AdRecommendation:
        self.current_step = "ad_recommendation"
        service = AdRecommendationService(self.db)
        recommendation = self.db.scalar(select(AdRecommendation).where(
            AdRecommendation.product_id == product.id
        ).order_by(AdRecommendation.id.desc()).limit(1))
        if recommendation is None:
            recommendation = service.generate(product.id, self.provider)
            self.created_any = True
        if recommendation.confirm_status == AdRecommendationConfirmStatus.PENDING:
            recommendation = service.confirm(
                product.id, recommendation.id,
                AdRecommendationConfirmation(
                    confirm_status=AdRecommendationConfirmStatus.CONFIRMED,
                    confirm_remark="Demo 初始化：管理员确认 Mock 投放建议",
                ),
                admin_user_id,
            )
            self.created_any = True
        if recommendation.confirm_status != AdRecommendationConfirmStatus.CONFIRMED:
            raise AppError(
                status_code=409, code="demo_recommendation_not_confirmed",
                message="Demo recommendation is not confirmed",
            )
        self.ids["ad_recommendation_id"] = recommendation.id
        self._done("ad_recommendation")
        return recommendation

    def _ensure_experiment(
        self, product: Product, recommendation: AdRecommendation,
        asset: GeneratedAsset, link: PromotionLink,
    ) -> AdExperiment:
        self.current_step = "ad_experiment"
        service = AdExperimentService(self.db)
        experiment = self.db.scalar(select(AdExperiment).where(
            AdExperiment.product_id == product.id,
            AdExperiment.ad_recommendation_id == recommendation.id,
        ).order_by(AdExperiment.id.desc()).limit(1))
        if experiment is None:
            experiment = service.generate(product.id, AdExperimentGenerate(
                recommendation_id=recommendation.id,
                related_asset_id=asset.id,
                related_link_id=link.id,
            ), self.provider)
            self.created_any = True
        if experiment.experiment_status == AdExperimentStatus.DRAFT:
            experiment = service.update_status(
                product.id, experiment.id,
                AdExperimentStatusUpdate(experiment_status=AdExperimentStatus.CONFIRMED),
            )
            self.created_any = True
        if experiment.experiment_status == AdExperimentStatus.CONFIRMED:
            experiment = service.update_status(
                product.id, experiment.id,
                AdExperimentStatusUpdate(experiment_status=AdExperimentStatus.RUNNING),
            )
            self.created_any = True
        if experiment.experiment_status not in {AdExperimentStatus.RUNNING, AdExperimentStatus.FINISHED}:
            raise AppError(
                status_code=409, code="demo_experiment_invalid_status",
                message="Demo experiment cannot record performance",
            )
        self.ids["ad_experiment_id"] = experiment.id
        self._done("ad_experiment_running")
        return experiment

    def _ensure_performance_records(
        self, product: Product, experiment: AdExperiment
    ) -> list[PerformanceRecord]:
        self.current_step = "performance_records"
        definitions = (
            ("2026-09-01T00:00:00+00:00", "2026-09-02T00:00:00+00:00", 12000, 720, 58, "800.00", "1460.00", "Demo Day 1 [Mock]"),
            ("2026-09-02T00:00:00+00:00", "2026-09-03T00:00:00+00:00", 15000, 825, 64, "920.00", "1680.00", "Demo Day 2 [Mock]"),
            ("2026-09-03T00:00:00+00:00", "2026-09-04T00:00:00+00:00", 18000, 1080, 91, "1050.00", "2240.00", "Demo Day 3 [Mock]"),
        )
        service = PerformanceRecordService(self.db)
        records = []
        for start, end, impressions, clicks, conversions, spend, revenue, notes in definitions:
            record = self.db.scalar(select(PerformanceRecord).where(
                PerformanceRecord.product_id == product.id,
                PerformanceRecord.notes == notes,
            ))
            if record is None:
                record = service.create(product.id, PerformanceRecordCreate(
                    generated_asset_id=experiment.related_asset_id,
                    promotion_link_id=experiment.related_link_id,
                    experiment_id=experiment.id,
                    period_start=datetime.fromisoformat(start),
                    period_end=datetime.fromisoformat(end),
                    impressions=impressions, clicks=clicks, conversions=conversions,
                    spend=Decimal(spend), revenue=Decimal(revenue), notes=notes,
                ))
                self.created_any = True
            records.append(record)
        if experiment.experiment_status == AdExperimentStatus.RUNNING:
            experiment = AdExperimentService(self.db).update_status(
                product.id, experiment.id,
                AdExperimentStatusUpdate(experiment_status=AdExperimentStatus.FINISHED),
            )
            self.created_any = True
        self.ids["performance_record_ids"] = [record.id for record in records]
        self._done("performance_records")
        self._done("ad_experiment_finished")
        return records

    def _ensure_review_report(self, product: Product) -> ReviewReport:
        self.current_step = "review_report"
        report = self.db.scalar(select(ReviewReport).where(
            ReviewReport.product_id == product.id,
            ReviewReport.period_start == DEMO_PERIOD_START,
            ReviewReport.period_end == DEMO_PERIOD_END,
        ).order_by(ReviewReport.id.desc()).limit(1))
        if report is None:
            report = ReviewReportService(self.db).generate(
                product.id,
                ReviewReportGenerate(
                    period_start=DEMO_PERIOD_START, period_end=DEMO_PERIOD_END
                ),
                self.provider,
            )
            self.created_any = True
        self.ids["review_report_id"] = report.id
        self._done("review_report")
        return report

    def _validate_consistency(self, product: Product, *objects: object) -> None:
        for obj in objects:
            if isinstance(obj, list):
                candidates = obj
            else:
                candidates = [obj]
            for candidate in candidates:
                if getattr(candidate, "product_id", product.id) != product.id:
                    raise AppError(
                        status_code=409, code="demo_product_consistency_error",
                        message="Demo objects do not belong to one product",
                    )

    def _find_store(self) -> Store | None:
        return self.db.scalar(select(Store).where(Store.store_name == DEMO_STORE_NAME))

    def _asset_for_job(self, job_id: int) -> GeneratedAsset | None:
        return self.db.scalar(select(GeneratedAsset).where(GeneratedAsset.generation_job_id == job_id))

    def _done(self, step: str) -> None:
        if step not in self.completed_steps:
            self.completed_steps.append(step)

    def _response(
        self, *, status: str, failed_step: str | None = None,
        error_code: str | None = None,
    ) -> DemoDataResponse:
        return DemoDataResponse(
            status=status, completed_steps=self.completed_steps,
            failed_step=failed_step, error_code=error_code,
            next_entry=(
                f"/api/v1/products/{self.ids['product_id']}"
                if self.ids.get("product_id") else None
            ),
            **self.ids,
        )
