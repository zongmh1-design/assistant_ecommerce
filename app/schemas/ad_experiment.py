"""Strict experiment Context, AI output and API schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.ad_experiment import AdExperimentStatus
from app.models.generated_asset import GeneratedAssetType
from app.models.store import Platform
from app.schemas.ad_recommendation import (
    AudienceSegment, BidStrategy, BudgetPlan, CreativeTest, RiskControl,
)
from app.schemas.promotion_link import PromotionUtm


class ExperimentProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    target_audience: str | None
    selling_points: list[str]


class ExperimentRecommendationContext(BaseModel):
    summary: str
    objective: str
    audience_segments: list[AudienceSegment]
    budget_plan: BudgetPlan
    creative_tests: list[CreativeTest]
    bid_strategy: BidStrategy
    risk_controls: list[RiskControl]
    next_steps: list[str]


class ExperimentAssetContext(BaseModel):
    asset_reference: str
    asset_type: GeneratedAssetType
    version_no: int
    usage_scene: str | None
    score: int | None
    tags_json: list[str]


class ExperimentLinkContext(BaseModel):
    link_reference: str
    link_name: str
    scene_text: str | None
    utm_json: PromotionUtm
    click_count: int


class AdExperimentContext(BaseModel):
    product: ExperimentProductContext
    confirmed_recommendation: ExperimentRecommendationContext
    approved_asset: ExperimentAssetContext | None
    active_promotion_link: ExperimentLinkContext | None


class AdExperimentOutput(BaseModel):
    experiment_name: str = Field(min_length=1, max_length=200)
    target_text: str = Field(min_length=1)
    audience_text: str = Field(min_length=1)
    budget_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    success_metric_text: str = Field(min_length=1)
    hypothesis_text: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class AdExperimentGenerate(BaseModel):
    recommendation_id: int = Field(gt=0)
    related_asset_id: int | None = Field(default=None, gt=0)
    related_link_id: int | None = Field(default=None, gt=0)
    model_config = ConfigDict(extra="forbid")


class AdExperimentUpdate(BaseModel):
    experiment_name: str | None = Field(default=None, min_length=1, max_length=200)
    target_text: str | None = Field(default=None, min_length=1)
    audience_text: str | None = Field(default=None, min_length=1)
    budget_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    success_metric_text: str | None = Field(default=None, min_length=1)
    hypothesis_text: str | None = Field(default=None, min_length=1)
    related_asset_id: int | None = Field(default=None, gt=0)
    related_link_id: int | None = Field(default=None, gt=0)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_null_content(self) -> "AdExperimentUpdate":
        nullable_relations = {"related_asset_id", "related_link_id"}
        for field_name in self.model_fields_set - nullable_relations:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class AdExperimentStatusUpdate(BaseModel):
    experiment_status: AdExperimentStatus
    model_config = ConfigDict(extra="forbid")


class AdExperimentRead(BaseModel):
    id: int
    product_id: int
    ad_recommendation_id: int
    related_asset_id: int | None
    related_link_id: int | None
    experiment_name: str
    target_text: str
    audience_text: str
    budget_amount: Decimal
    success_metric_text: str
    hypothesis_text: str
    experiment_status: AdExperimentStatus
    provider_name: str | None
    model_name: str | None
    usage_json: dict[str, int] | None
    input_context_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdExperimentListResponse(BaseModel):
    items: list[AdExperimentRead]
    total: int
    page: int
    page_size: int
