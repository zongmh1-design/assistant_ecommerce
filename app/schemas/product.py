"""Create, update, read and paginated response schemas for Product."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.product import ProductStatus
from app.models.store import Platform


Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductCreate(BaseModel):
    store_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    platform: Platform
    category: str | None = Field(default=None, max_length=100)
    price: Money
    cost: Money | None = None
    target_audience: str | None = None
    selling_points: list[str] = Field(default_factory=list)
    product_url: str | None = Field(default=None, max_length=2048)
    images_json: list[str] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.DRAFT


class ProductUpdate(BaseModel):
    store_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: Platform | None = None
    category: str | None = Field(default=None, max_length=100)
    price: Money | None = None
    cost: Money | None = None
    target_audience: str | None = None
    selling_points: list[str] | None = None
    product_url: str | None = Field(default=None, max_length=2048)
    images_json: list[str] | None = None
    status: ProductStatus | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "ProductUpdate":
        required_fields = (
            "store_id",
            "name",
            "platform",
            "price",
            "selling_points",
            "images_json",
            "status",
        )
        for field_name in required_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductRead(BaseModel):
    id: int
    store_id: int
    name: str
    platform: Platform
    category: str | None
    price: Decimal
    cost: Decimal | None
    target_audience: str | None
    selling_points: list[str]
    product_url: str | None
    images_json: list[str]
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
