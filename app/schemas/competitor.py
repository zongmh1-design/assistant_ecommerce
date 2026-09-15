"""API schemas for competitors and public-link parsing tasks."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models.competitor import PublicLinkParseTaskStatus
from app.models.store import Platform


CompetitorMoney = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platform: Platform
    url: HttpUrl
    price: CompetitorMoney | None = None
    sales_hint: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    main_image: HttpUrl | None = None
    selling_points: list[str] = Field(default_factory=list)
    review_keywords: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: Platform | None = None
    url: HttpUrl | None = None
    price: CompetitorMoney | None = None
    sales_hint: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    main_image: HttpUrl | None = None
    selling_points: list[str] | None = None
    review_keywords: list[str] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "CompetitorUpdate":
        for field_name in ("name", "platform", "url", "selling_points", "review_keywords"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CompetitorRead(BaseModel):
    id: int
    product_id: int
    name: str
    platform: Platform
    url: str
    price: Decimal | None
    sales_hint: str | None
    title: str | None
    main_image: str | None
    selling_points: list[str]
    review_keywords: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorListResponse(BaseModel):
    items: list[CompetitorRead]
    total: int
    page: int
    page_size: int


class PublicLinkParseTaskCreate(BaseModel):
    source_url: HttpUrl

    model_config = ConfigDict(extra="forbid")


class PublicLinkParseTaskRead(BaseModel):
    id: int
    product_id: int
    source_url: str
    task_status: PublicLinkParseTaskStatus
    attempts: int
    result_json: dict[str, Any] | None
    error_message: str | None
    confirmed_competitor_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
