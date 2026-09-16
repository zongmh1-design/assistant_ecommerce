"""Strict AI input, structured output and REST schemas for product diagnosis."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.store import Platform


class DiagnosisProductContext(BaseModel):
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    cost: Decimal | None
    target_audience: str | None
    selling_points: list[str]


class DiagnosisCompetitorContext(BaseModel):
    name: str
    platform: Platform
    price: Decimal | None
    title: str | None
    sales_hint: str | None
    selling_points: list[str]
    review_keywords: list[str]


class ProductDiagnosisContext(BaseModel):
    product: DiagnosisProductContext
    competitors: list[DiagnosisCompetitorContext]


class ProductDiagnosisOutput(BaseModel):
    positioning: str = Field(min_length=1)
    price_band: str = Field(min_length=1)
    audience_insights: list[str] = Field(min_length=1)
    pain_points: list[str] = Field(min_length=1)
    selling_point_analysis: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    recommendations: list[str] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class ProductDiagnosisUpdate(BaseModel):
    positioning: str | None = Field(default=None, min_length=1)
    price_band: str | None = Field(default=None, min_length=1)
    audience_insights: list[str] | None = Field(default=None, min_length=1)
    pain_points: list[str] | None = Field(default=None, min_length=1)
    selling_point_analysis: list[str] | None = Field(default=None, min_length=1)
    risks: list[str] | None = Field(default=None, min_length=1)
    recommendations: list[str] | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_explicit_null(self) -> "ProductDiagnosisUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductDiagnosisRead(ProductDiagnosisOutput):
    id: int
    product_id: int
    source_type: str
    provider_name: str | None
    model_name: str | None
    usage_json: dict[str, int] | None
    input_context_json: dict[str, object]
    raw_output: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDiagnosisListResponse(BaseModel):
    items: list[ProductDiagnosisRead]
    total: int
    page: int
    page_size: int
