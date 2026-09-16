"""Manual performance input and derived-metric response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


Money = Decimal


class PerformanceRecordCreate(BaseModel):
    creative_plan_id: int | None = Field(default=None, gt=0)
    generated_asset_id: int | None = Field(default=None, gt=0)
    promotion_link_id: int | None = Field(default=None, gt=0)
    experiment_id: int | None = Field(default=None, gt=0)
    period_start: AwareDatetime
    period_end: AwareDatetime
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    conversions: int = Field(ge=0)
    spend: Money = Field(ge=0, max_digits=14, decimal_places=2)
    revenue: Money = Field(ge=0, max_digits=14, decimal_places=2)
    notes: str | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_business_values(self) -> "PerformanceRecordCreate":
        _validate_values(
            self.period_start, self.period_end,
            self.impressions, self.clicks, self.conversions,
        )
        return self


class PerformanceRecordUpdate(BaseModel):
    creative_plan_id: int | None = Field(default=None, gt=0)
    generated_asset_id: int | None = Field(default=None, gt=0)
    promotion_link_id: int | None = Field(default=None, gt=0)
    experiment_id: int | None = Field(default=None, gt=0)
    period_start: AwareDatetime | None = None
    period_end: AwareDatetime | None = None
    impressions: int | None = Field(default=None, ge=0)
    clicks: int | None = Field(default=None, ge=0)
    conversions: int | None = Field(default=None, ge=0)
    spend: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    revenue: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_null_required_values(self) -> "PerformanceRecordUpdate":
        nullable = {
            "creative_plan_id", "generated_asset_id", "promotion_link_id",
            "experiment_id", "notes",
        }
        for field_name in self.model_fields_set - nullable:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PerformanceRecordRead(BaseModel):
    id: int
    product_id: int
    creative_plan_id: int | None
    generated_asset_id: int | None
    promotion_link_id: int | None
    experiment_id: int | None
    period_start: datetime
    period_end: datetime
    impressions: int
    clicks: int
    ctr: Decimal
    conversions: int
    conversion_rate: Decimal
    spend: Decimal
    revenue: Decimal
    roi: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PerformanceRecordListResponse(BaseModel):
    items: list[PerformanceRecordRead]
    total: int
    page: int
    page_size: int


def _validate_values(
    period_start: datetime,
    period_end: datetime,
    impressions: int,
    clicks: int,
    conversions: int,
) -> None:
    if period_end <= period_start:
        raise ValueError("period_end must be later than period_start")
    if clicks > impressions:
        raise ValueError("clicks cannot exceed impressions")
    if conversions > clicks:
        raise ValueError("conversions cannot exceed clicks")
