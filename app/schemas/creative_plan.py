"""Creative context, strict AI outputs and editable CreativePlan schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.creative_plan import CreativePlanStatus, CreativePlanType
from app.models.store import Platform


NonEmptyText = Annotated[str, Field(min_length=1)]


class CreativeProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    target_audience: str | None
    selling_points: list[str]


class CreativeDiagnosisContext(BaseModel):
    positioning: str
    price_band: str
    audience_insights: list[str]
    pain_points: list[str]
    selling_point_analysis: list[str]
    risks: list[str]
    recommendations: list[str]


class CreativePlanContext(BaseModel):
    product: CreativeProductContext
    diagnosis: CreativeDiagnosisContext | None


class MainImagePlanContent(BaseModel):
    visual_structure: list[NonEmptyText] = Field(min_length=1)
    core_copy: list[NonEmptyText] = Field(min_length=1)
    highlighted_selling_points: list[NonEmptyText] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class MainImagePlanItem(MainImagePlanContent):
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1)


class MainImagePlansOutput(BaseModel):
    plans: list[MainImagePlanItem] = Field(min_length=3, max_length=3)

    model_config = ConfigDict(extra="forbid")


class StoryboardScene(BaseModel):
    scene_no: int = Field(ge=1)
    visual: str = Field(min_length=1)
    duration_hint: str = Field(min_length=1)
    voiceover: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class VideoScriptContent(BaseModel):
    opening_hook: str = Field(min_length=1)
    storyboard: list[StoryboardScene] = Field(min_length=1)
    voiceover: list[NonEmptyText] = Field(min_length=1)
    conversion_cta: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class VideoScriptItem(VideoScriptContent):
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1)


class VideoScriptsOutput(BaseModel):
    scripts: list[VideoScriptItem] = Field(min_length=3, max_length=3)

    model_config = ConfigDict(extra="forbid")


class CreativePlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_json: dict[str, Any] | None = None
    rationale_text: str | None = Field(default=None, min_length=1)
    status: CreativePlanStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_explicit_null(self) -> "CreativePlanUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CreativePlanRead(BaseModel):
    id: int
    product_id: int
    plan_type: CreativePlanType
    title: str
    content_json: dict[str, Any]
    rationale_text: str
    status: CreativePlanStatus
    provider_name: str | None
    model_name: str | None
    usage_json: dict[str, int] | None
    input_context_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreativePlanListResponse(BaseModel):
    items: list[CreativePlanRead]
    total: int
    page: int
    page_size: int
