"""Promotion-link context, suggestion, CRUD and click schemas."""

from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from app.models.creative_plan import CreativePlanType
from app.models.generated_asset import GeneratedAssetType
from app.models.promotion_link import PromotionLinkStatus
from app.models.store import Platform


class PromotionUtm(BaseModel):
    utm_source: str | None = Field(default=None, max_length=200)
    utm_medium: str | None = Field(default=None, max_length=200)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)
    utm_term: str | None = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")


class PromotionProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    target_audience: str | None
    selling_points: list[str]


class PromotionCreativePlanContext(BaseModel):
    plan_type: CreativePlanType
    title: str
    content_json: dict[str, Any]


class PromotionAssetContext(BaseModel):
    asset_type: GeneratedAssetType
    usage_scene: str | None
    tags_json: list[str]


class PromotionLinkSuggestionContext(BaseModel):
    product: PromotionProductContext
    selected_creative_plan: PromotionCreativePlanContext | None
    approved_asset: PromotionAssetContext | None


class PromotionLinkSuggestion(BaseModel):
    link_name: str = Field(min_length=1, max_length=200)
    scene_text: str = Field(min_length=1, max_length=300)
    utm_source: str = Field(min_length=1, max_length=200)
    utm_medium: str = Field(min_length=1, max_length=200)
    utm_campaign: str = Field(min_length=1, max_length=200)
    utm_content: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class PromotionLinkCreate(BaseModel):
    link_name: str = Field(min_length=1, max_length=200)
    target_url: AnyHttpUrl
    utm_json: PromotionUtm = Field(default_factory=PromotionUtm)
    scene_text: str | None = Field(default=None, max_length=300)

    model_config = ConfigDict(extra="forbid")


class PromotionLinkUpdate(BaseModel):
    link_name: str | None = Field(default=None, min_length=1, max_length=200)
    target_url: AnyHttpUrl | None = None
    utm_json: PromotionUtm | None = None
    scene_text: str | None = Field(default=None, max_length=300)
    status: PromotionLinkStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_required_nulls(self) -> "PromotionLinkUpdate":
        for field_name in ("link_name", "target_url", "utm_json", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PromotionLinkRead(BaseModel):
    id: int
    product_id: int
    link_name: str
    target_url: AnyHttpUrl
    tracking_code: str
    utm_json: PromotionUtm
    status: PromotionLinkStatus
    click_count: int
    scene_text: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromotionLinkListResponse(BaseModel):
    items: list[PromotionLinkRead]
    total: int
    page: int
    page_size: int


class PromotionLinkClickRead(BaseModel):
    id: int
    promotion_link_id: int
    clicked_at: datetime
    client_ip: str | None
    user_agent: str | None

    model_config = ConfigDict(from_attributes=True)


class PromotionLinkClickListResponse(BaseModel):
    items: list[PromotionLinkClickRead]
    total: int
    page: int
    page_size: int
