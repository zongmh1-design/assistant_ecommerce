"""Strict advertising recommendation Context, AI output and API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.ad_recommendation import AdRecommendationConfirmStatus
from app.models.creative_plan import CreativePlanType
from app.models.generated_asset import GeneratedAssetType
from app.models.store import Platform
from app.schemas.promotion_link import PromotionUtm


NonEmptyText = Annotated[str, Field(min_length=1)]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class AdProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    target_audience: str | None
    selling_points: list[str]


class AdDiagnosisContext(BaseModel):
    positioning: str
    audience_insights: list[str]
    pain_points: list[str]
    selling_point_analysis: list[str]
    risks: list[str]
    recommendations: list[str]


class AdCreativePlanContext(BaseModel):
    plan_type: CreativePlanType
    title: str
    content_json: dict[str, object]


class AdAssetContext(BaseModel):
    asset_reference: str
    asset_type: GeneratedAssetType
    version_no: int
    usage_scene: str | None
    score: int | None
    tags_json: list[str]


class AdPromotionLinkContext(BaseModel):
    link_name: str
    scene_text: str | None
    utm_json: PromotionUtm
    click_count: int


class AdRecommendationContext(BaseModel):
    product: AdProductContext
    latest_diagnosis: AdDiagnosisContext | None
    selected_creative_plans: list[AdCreativePlanContext]
    approved_assets: list[AdAssetContext]
    active_promotion_links: list[AdPromotionLinkContext]


class AudienceSegment(BaseModel):
    segment_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class BudgetAllocation(BaseModel):
    channel_or_test: str = Field(min_length=1)
    amount: Money
    rationale: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class BudgetPlan(BaseModel):
    total_budget: Money
    currency: str = Field(min_length=3, max_length=3)
    allocation: list[BudgetAllocation] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def allocation_matches_total(self) -> "BudgetPlan":
        allocated = sum(
            (item.amount for item in self.allocation),
            start=Decimal("0"),
        )
        if allocated != self.total_budget:
            raise ValueError("allocation amount must equal total_budget")
        return self


class CreativeTest(BaseModel):
    test_name: str = Field(min_length=1)
    asset_reference: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    success_metric: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class BidStrategy(BaseModel):
    strategy_name: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    constraints: list[NonEmptyText] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class RiskControl(BaseModel):
    risk: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class AdRecommendationOutput(BaseModel):
    summary: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    audience_segments: list[AudienceSegment] = Field(min_length=1)
    budget_plan: BudgetPlan
    creative_tests: list[CreativeTest] = Field(min_length=1)
    bid_strategy: BidStrategy
    risk_controls: list[RiskControl] = Field(min_length=1)
    next_steps: list[NonEmptyText] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class AdRecommendationUpdate(BaseModel):
    summary_text: str | None = Field(default=None, min_length=1)
    objective_text: str | None = Field(default=None, min_length=1)
    audience_segments_json: list[AudienceSegment] | None = Field(default=None, min_length=1)
    budget_plan_json: BudgetPlan | None = None
    creative_tests_json: list[CreativeTest] | None = Field(default=None, min_length=1)
    bid_strategy_json: BidStrategy | None = None
    risk_controls_json: list[RiskControl] | None = Field(default=None, min_length=1)
    next_steps_json: list[NonEmptyText] | None = Field(default=None, min_length=1)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_explicit_null(self) -> "AdRecommendationUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class AdRecommendationConfirmation(BaseModel):
    confirm_status: AdRecommendationConfirmStatus
    confirm_remark: str | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_terminal_status(self) -> "AdRecommendationConfirmation":
        if self.confirm_status == AdRecommendationConfirmStatus.PENDING:
            raise ValueError("confirm_status must be confirmed or rejected")
        return self


class AdRecommendationRead(BaseModel):
    id: int
    product_id: int
    summary_text: str
    objective_text: str
    audience_segments_json: list[AudienceSegment]
    budget_plan_json: BudgetPlan
    creative_tests_json: list[CreativeTest]
    bid_strategy_json: BidStrategy
    risk_controls_json: list[RiskControl]
    next_steps_json: list[str]
    confirm_status: AdRecommendationConfirmStatus
    confirmed_by: int | None
    confirmed_at: datetime | None
    confirm_remark: str | None
    provider_name: str | None
    model_name: str | None
    usage_json: dict[str, int] | None
    input_context_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdRecommendationListResponse(BaseModel):
    items: list[AdRecommendationRead]
    total: int
    page: int
    page_size: int
