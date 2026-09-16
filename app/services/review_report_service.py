"""Aggregate factual metrics before asking the LLM to explain performance."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.llm_provider import (
    InvalidLLMOutputError, LLMAuthenticationError, LLMConfigurationError,
    LLMProvider, LLMProviderError, LLMRateLimitError, LLMTimeoutError,
    StructuredLLMResult,
)
from app.ai.prompts.review_report import REVIEW_REPORT_SYSTEM_PROMPT, build_review_report_user_prompt
from app.core.exceptions import AppError
from app.models.performance_record import PerformanceRecord
from app.models.product import Product
from app.models.review_report import ReviewReport
from app.repositories.product_repository import ProductRepository
from app.repositories.review_report_repository import ReviewReportRepository
from app.schemas.review_report import (
    AggregatedPerformance, AssetReviewSummary, ExperimentReviewSummary,
    PromotionLinkReviewSummary, ReviewPeriodContext, ReviewProductContext,
    ReviewReportContext, ReviewReportGenerate, ReviewReportOutput, ReviewReportUpdate,
)
from app.services.performance_record_service import PerformanceRecordService


class ReviewReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.reports = ReviewReportRepository(db)

    def generate(
        self, product_id: int, payload: ReviewReportGenerate, provider: LLMProvider
    ) -> ReviewReport:
        product = self._require_product(product_id)
        records = self.reports.list_source_records(
            product_id, payload.period_start, payload.period_end
        )
        if not records:
            raise AppError(
                status_code=409, code="no_performance_data",
                message="No fully contained performance records exist in the requested period",
            )
        excluded_count = self.reports.count_excluded_overlapping_records(
            product_id, payload.period_start, payload.period_end
        )
        context = self._build_context(product, payload, records, excluded_count)
        result = self._call_provider(provider, build_review_report_user_prompt(context))
        output = _validate_output(result)
        report = ReviewReport(
            product_id=product_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            summary_text=output.summary,
            insights_json=_json(output.insights),
            problem_judgements_json=_json(output.problem_judgements),
            next_actions_json=_json(output.next_actions),
            provider_name=result.provider_name,
            model_name=result.model_name,
            usage_json=result.usage,
            input_context_json=context.model_dump(mode="json"),
        )
        self.reports.add(report)
        return self._commit_and_refresh(report)

    def list(
        self, *, product_id: int, period_start_from: datetime | None,
        period_end_to: datetime | None, page: int, page_size: int,
    ) -> tuple[list[ReviewReport], int]:
        self._require_product(product_id)
        return self.reports.list_by_product(
            product_id=product_id,
            period_start_from=period_start_from,
            period_end_to=period_end_to,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, report_id: int) -> ReviewReport:
        self._require_product(product_id)
        report = self.reports.get_by_id_and_product_id(report_id, product_id)
        if report is None:
            raise _not_found(report_id)
        return report

    def update(
        self, product_id: int, report_id: int, payload: ReviewReportUpdate
    ) -> ReviewReport:
        self._require_product(product_id)
        report = self.reports.get_by_id_and_product_id(report_id, product_id)
        if report is None:
            raise _not_found(report_id)
        self.reports.update(
            report, payload.model_dump(mode="json", exclude_unset=True)
        )
        return self._commit_and_refresh(report)

    def _build_context(
        self, product: Product, payload: ReviewReportGenerate,
        records: list[PerformanceRecord], excluded_count: int,
    ) -> ReviewReportContext:
        experiment_groups: dict[int, list[PerformanceRecord]] = defaultdict(list)
        asset_groups: dict[int, list[PerformanceRecord]] = defaultdict(list)
        link_groups: dict[int, list[PerformanceRecord]] = defaultdict(list)
        for record in records:
            if record.experiment_id is not None:
                experiment_groups[record.experiment_id].append(record)
            if record.generated_asset_id is not None:
                asset_groups[record.generated_asset_id].append(record)
            if record.promotion_link_id is not None:
                link_groups[record.promotion_link_id].append(record)

        experiment_summaries = []
        for position, group_id in enumerate(sorted(experiment_groups), start=1):
            grouped = experiment_groups[group_id]
            experiment = grouped[0].experiment
            if experiment is None:
                continue
            experiment_summaries.append(ExperimentReviewSummary(
                experiment_reference=f"experiment_{position}",
                experiment_name=experiment.experiment_name,
                hypothesis_text=experiment.hypothesis_text,
                success_metric_text=experiment.success_metric_text,
                experiment_status=experiment.experiment_status,
                metrics=self._aggregate(grouped),
            ))

        asset_summaries = []
        for position, group_id in enumerate(sorted(asset_groups), start=1):
            grouped = asset_groups[group_id]
            asset = grouped[0].generated_asset
            if asset is None:
                continue
            asset_summaries.append(AssetReviewSummary(
                asset_reference=f"asset_{position}_{asset.asset_type.value}_v{asset.version_no}",
                asset_type=asset.asset_type,
                version_no=asset.version_no,
                usage_scene=asset.usage_scene,
                score=asset.score,
                tags=asset.tags_json,
                metrics=self._aggregate(grouped),
            ))

        link_summaries = []
        for position, group_id in enumerate(sorted(link_groups), start=1):
            grouped = link_groups[group_id]
            link = grouped[0].promotion_link
            if link is None:
                continue
            link_summaries.append(PromotionLinkReviewSummary(
                link_reference=f"promotion_link_{position}",
                link_name=link.link_name,
                scene_text=link.scene_text,
                metrics=self._aggregate(grouped),
            ))

        return ReviewReportContext(
            product=ReviewProductContext(
                name=product.name, platform=product.platform, category=product.category,
                price=product.price, target_audience=product.target_audience,
                selling_points=product.selling_points,
            ),
            review_period=ReviewPeriodContext(
                period_start=payload.period_start, period_end=payload.period_end,
                included_count=len(records), excluded_count=excluded_count,
            ),
            aggregated_performance=self._aggregate(records),
            experiment_summaries=experiment_summaries,
            asset_summaries=asset_summaries,
            promotion_link_summaries=link_summaries,
        )

    @staticmethod
    def _aggregate(records: list[PerformanceRecord]) -> AggregatedPerformance:
        impressions = sum(record.impressions for record in records)
        clicks = sum(record.clicks for record in records)
        conversions = sum(record.conversions for record in records)
        spend = sum((record.spend for record in records), start=Decimal("0.00"))
        revenue = sum((record.revenue for record in records), start=Decimal("0.00"))
        metrics = PerformanceRecordService.calculate_metrics(
            impressions, clicks, conversions, spend, revenue
        )
        return AggregatedPerformance(
            total_impressions=impressions,
            total_clicks=clicks,
            total_conversions=conversions,
            total_spend=spend,
            total_revenue=revenue,
            overall_ctr=metrics.ctr,
            overall_conversion_rate=metrics.conversion_rate,
            overall_roi=metrics.roi,
        )

    def _call_provider(self, provider: LLMProvider, user_prompt: str) -> StructuredLLMResult:
        try:
            return provider.generate_structured(
                system_prompt=REVIEW_REPORT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=ReviewReportOutput,
            )
        except LLMConfigurationError as exc:
            raise _provider_error(503, "llm_configuration_error", "LLM provider is not configured") from exc
        except LLMAuthenticationError as exc:
            raise _provider_error(502, "llm_authentication_error", "LLM provider rejected authentication") from exc
        except LLMRateLimitError as exc:
            raise _provider_error(503, "llm_rate_limit_error", "LLM provider rate limit was reached") from exc
        except LLMTimeoutError as exc:
            raise _provider_error(504, "llm_timeout_error", "LLM provider request timed out") from exc
        except InvalidLLMOutputError as exc:
            raise _invalid_output() from exc
        except LLMProviderError as exc:
            raise _provider_error(502, "llm_provider_error", "Review report provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Review report provider call failed unexpectedly") from exc

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404, code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def _commit_and_refresh(self, report: ReviewReport) -> ReviewReport:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(report)
        return report


def _json(items: list[object]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in items]


def _validate_output(result: StructuredLLMResult) -> ReviewReportOutput:
    try:
        if not result.raw_output.strip():
            raise ValueError("raw_output is empty")
        return ReviewReportOutput.model_validate(result.data)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise _invalid_output() from exc


def _not_found(report_id: int) -> AppError:
    return AppError(
        status_code=404, code="review_report_not_found",
        message=f"Review report {report_id} was not found",
    )


def _invalid_output() -> AppError:
    return AppError(
        status_code=502, code="invalid_llm_output",
        message="Review report provider returned invalid structured output",
    )


def _provider_error(status_code: int, code: str, message: str) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
