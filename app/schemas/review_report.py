"""Strict review context, structured AI output and REST schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.ad_experiment import AdExperimentStatus
from app.models.generated_asset import GeneratedAssetType
from app.models.store import Platform


NonEmptyText = Annotated[str, Field(min_length=1)]


class ReviewReportGenerate(BaseModel):
    period_start: AwareDatetime
    period_end: AwareDatetime
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_period(self) -> "ReviewReportGenerate":
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be later than period_start")
        return self


class ReviewProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    target_audience: str | None
    selling_points: list[str]


class ReviewPeriodContext(BaseModel):
    period_start: datetime
    period_end: datetime
    included_count: int
    excluded_count: int


class AggregatedPerformance(BaseModel):
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_spend: Decimal
    total_revenue: Decimal
    overall_ctr: Decimal
    overall_conversion_rate: Decimal
    overall_roi: Decimal | None


class ExperimentReviewSummary(BaseModel):
    experiment_reference: str
    experiment_name: str
    hypothesis_text: str
    success_metric_text: str
    experiment_status: AdExperimentStatus
    metrics: AggregatedPerformance


class AssetReviewSummary(BaseModel):
    asset_reference: str
    asset_type: GeneratedAssetType
    version_no: int
    usage_scene: str | None
    score: int | None
    tags: list[str]
    metrics: AggregatedPerformance


class PromotionLinkReviewSummary(BaseModel):
    link_reference: str
    link_name: str
    scene_text: str | None
    metrics: AggregatedPerformance


class ReviewReportContext(BaseModel):
    product: ReviewProductContext
    review_period: ReviewPeriodContext
    aggregated_performance: AggregatedPerformance
    experiment_summaries: list[ExperimentReviewSummary]
    asset_summaries: list[AssetReviewSummary]
    promotion_link_summaries: list[PromotionLinkReviewSummary]


class ReviewInsight(BaseModel):
    title: str = Field(min_length=1)
    finding: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ProblemJudgement(BaseModel):
    problem: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    severity: Literal["low", "medium", "high"]
    model_config = ConfigDict(extra="forbid")


class ReviewNextAction(BaseModel):
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    priority: Literal["high", "medium", "low"]
    model_config = ConfigDict(extra="forbid")


class ReviewReportOutput(BaseModel):
    summary: str = Field(min_length=1)
    insights: list[ReviewInsight] = Field(min_length=1)
    problem_judgements: list[ProblemJudgement] = Field(min_length=1)
    next_actions: list[ReviewNextAction] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ReviewReportUpdate(BaseModel):
    summary_text: str | None = Field(default=None, min_length=1)
    insights_json: list[ReviewInsight] | None = Field(default=None, min_length=1)
    problem_judgements_json: list[ProblemJudgement] | None = Field(default=None, min_length=1)
    next_actions_json: list[ReviewNextAction] | None = Field(default=None, min_length=1)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_explicit_null(self) -> "ReviewReportUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ReviewReportRead(BaseModel):
    id: int
    product_id: int
    period_start: datetime
    period_end: datetime
    summary_text: str
    insights_json: list[ReviewInsight]
    problem_judgements_json: list[ProblemJudgement]
    next_actions_json: list[ReviewNextAction]
    provider_name: str | None
    model_name: str | None
    usage_json: dict[str, int] | None
    input_context_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewReportListResponse(BaseModel):
    items: list[ReviewReportRead]
    total: int
    page: int
    page_size: int
