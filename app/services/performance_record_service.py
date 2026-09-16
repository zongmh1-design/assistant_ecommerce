"""Validate manual metrics and calculate all derived performance values."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.ad_experiment import AdExperimentStatus
from app.models.performance_record import PerformanceRecord
from app.models.product import Product
from app.repositories.ad_experiment_repository import AdExperimentRepository
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.performance_record_repository import PerformanceRecordRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_link_repository import PromotionLinkRepository
from app.schemas.performance_record import PerformanceRecordCreate, PerformanceRecordUpdate


RATIO_QUANTUM = Decimal("0.000001")
ZERO_RATIO = Decimal("0.000000")


@dataclass(frozen=True)
class CalculatedMetrics:
    ctr: Decimal
    conversion_rate: Decimal
    roi: Decimal | None


@dataclass(frozen=True)
class PreparedPerformanceRecord:
    values: dict[str, object]
    metrics: CalculatedMetrics


class PerformanceRecordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.creative_plans = CreativePlanRepository(db)
        self.assets = GeneratedAssetRepository(db)
        self.links = PromotionLinkRepository(db)
        self.experiments = AdExperimentRepository(db)
        self.records = PerformanceRecordRepository(db)

    def create(
        self, product_id: int, payload: PerformanceRecordCreate
    ) -> PerformanceRecord:
        prepared = self.validate_and_prepare(product_id, payload)
        record = PerformanceRecord(
            product_id=product_id,
            **prepared.values,
            ctr=prepared.metrics.ctr,
            conversion_rate=prepared.metrics.conversion_rate,
            roi=prepared.metrics.roi,
        )
        self.records.add(record)
        return self._commit_and_refresh(record)

    def validate_and_prepare(
        self, product_id: int, payload: PerformanceRecordCreate
    ) -> PreparedPerformanceRecord:
        """Validate without writing, so manual create and file import share rules."""
        self._require_product(product_id)
        values = payload.model_dump()
        self._validate_relations(product_id, values, set(values))
        self._validate_business_values(**_raw_values(values))
        metrics = self.calculate_metrics(
            values["impressions"], values["clicks"], values["conversions"],
            values["spend"], values["revenue"],
        )
        return PreparedPerformanceRecord(values=values, metrics=metrics)

    def require_product_exists(self, product_id: int) -> Product:
        """Public read-only guard used before validating an import file."""
        return self._require_product(product_id)

    def update(
        self, product_id: int, record_id: int, payload: PerformanceRecordUpdate
    ) -> PerformanceRecord:
        self._require_product(product_id)
        record = self.records.get_for_update_by_id_and_product_id(record_id, product_id)
        if record is None:
            raise _not_found(record_id)

        changes = payload.model_dump(exclude_unset=True)
        self._validate_relations(product_id, changes, payload.model_fields_set)
        merged = {
            "period_start": changes.get("period_start", record.period_start),
            "period_end": changes.get("period_end", record.period_end),
            "impressions": changes.get("impressions", record.impressions),
            "clicks": changes.get("clicks", record.clicks),
            "conversions": changes.get("conversions", record.conversions),
            "spend": changes.get("spend", record.spend),
            "revenue": changes.get("revenue", record.revenue),
        }
        self._validate_business_values(**merged)
        metrics = self.calculate_metrics(
            merged["impressions"], merged["clicks"], merged["conversions"],
            merged["spend"], merged["revenue"],
        )
        changes.update(
            ctr=metrics.ctr,
            conversion_rate=metrics.conversion_rate,
            roi=metrics.roi,
        )
        self.records.update(record, changes)
        return self._commit_and_refresh(record)

    def list(
        self,
        *,
        product_id: int,
        experiment_id: int | None,
        generated_asset_id: int | None,
        promotion_link_id: int | None,
        period_start_from: datetime | None,
        period_end_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PerformanceRecord], int]:
        self._require_product(product_id)
        return self.records.list_by_product(
            product_id=product_id,
            experiment_id=experiment_id,
            generated_asset_id=generated_asset_id,
            promotion_link_id=promotion_link_id,
            period_start_from=period_start_from,
            period_end_to=period_end_to,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, record_id: int) -> PerformanceRecord:
        self._require_product(product_id)
        record = self.records.get_by_id_and_product_id(record_id, product_id)
        if record is None:
            raise _not_found(record_id)
        return record

    @staticmethod
    def calculate_metrics(
        impressions: int,
        clicks: int,
        conversions: int,
        spend: Decimal,
        revenue: Decimal,
    ) -> CalculatedMetrics:
        ctr = (
            (Decimal(clicks) / Decimal(impressions)).quantize(
                RATIO_QUANTUM, rounding=ROUND_HALF_UP
            )
            if impressions > 0 else ZERO_RATIO
        )
        conversion_rate = (
            (Decimal(conversions) / Decimal(clicks)).quantize(
                RATIO_QUANTUM, rounding=ROUND_HALF_UP
            )
            if clicks > 0 else ZERO_RATIO
        )
        roi = (
            ((revenue - spend) / spend).quantize(
                RATIO_QUANTUM, rounding=ROUND_HALF_UP
            )
            if spend > 0 else None
        )
        return CalculatedMetrics(ctr=ctr, conversion_rate=conversion_rate, roi=roi)

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404, code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def _validate_relations(
        self, product_id: int, values: dict[str, object], supplied_fields: set[str]
    ) -> None:
        checks = (
            ("creative_plan_id", self.creative_plans, "creative_plan_not_found", "Creative plan"),
            ("generated_asset_id", self.assets, "generated_asset_not_found", "Generated asset"),
            ("promotion_link_id", self.links, "promotion_link_not_found", "Promotion link"),
        )
        for field_name, repository, code, label in checks:
            if field_name not in supplied_fields or values.get(field_name) is None:
                continue
            relation_id = int(values[field_name])
            if repository.get_by_id_and_product_id(relation_id, product_id) is None:
                raise AppError(
                    status_code=404, code=code,
                    message=f"{label} {relation_id} was not found",
                )

        if "experiment_id" not in supplied_fields or values.get("experiment_id") is None:
            return
        experiment_id = int(values["experiment_id"])
        experiment = self.experiments.get_by_id_and_product_id(experiment_id, product_id)
        if experiment is None:
            raise AppError(
                status_code=404, code="ad_experiment_not_found",
                message=f"Ad experiment {experiment_id} was not found",
            )
        if experiment.experiment_status not in {
            AdExperimentStatus.RUNNING, AdExperimentStatus.FINISHED,
        }:
            raise AppError(
                status_code=409, code="ad_experiment_not_started",
                message="Performance can only be recorded for running or finished experiments",
            )

    @staticmethod
    def _validate_business_values(
        *, period_start: datetime, period_end: datetime,
        impressions: int, clicks: int, conversions: int,
        spend: Decimal, revenue: Decimal,
    ) -> None:
        if _as_utc(period_end) <= _as_utc(period_start):
            raise _invalid("period_end must be later than period_start")
        if impressions < 0 or clicks < 0 or conversions < 0:
            raise _invalid("Performance counts cannot be negative")
        if clicks > impressions:
            raise _invalid("clicks cannot exceed impressions")
        if conversions > clicks:
            raise _invalid("conversions cannot exceed clicks")
        if spend < 0 or revenue < 0:
            raise _invalid("spend and revenue cannot be negative")

    def _commit_and_refresh(self, record: PerformanceRecord) -> PerformanceRecord:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(record)
        return record


def _raw_values(values: dict[str, object]) -> dict[str, object]:
    return {
        key: values[key]
        for key in (
            "period_start", "period_end", "impressions", "clicks",
            "conversions", "spend", "revenue",
        )
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _invalid(message: str) -> AppError:
    return AppError(status_code=422, code="invalid_performance_record", message=message)


def _not_found(record_id: int) -> AppError:
    return AppError(
        status_code=404, code="performance_record_not_found",
        message=f"Performance record {record_id} was not found",
    )
