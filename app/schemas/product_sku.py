"""Create, update, read and list schemas for ProductSku."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.product_sku import ProductSkuStatus


SkuMoney = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductSkuCreate(BaseModel):
    sku_code: str = Field(min_length=1, max_length=100)
    sku_name: str = Field(min_length=1, max_length=200)
    spec_json: dict[str, str] = Field(default_factory=dict)
    price: SkuMoney
    cost: SkuMoney | None = None
    status: ProductSkuStatus = ProductSkuStatus.ACTIVE
    platform_sku_id: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ProductSkuUpdate(BaseModel):
    sku_code: str | None = Field(default=None, min_length=1, max_length=100)
    sku_name: str | None = Field(default=None, min_length=1, max_length=200)
    spec_json: dict[str, str] | None = None
    price: SkuMoney | None = None
    cost: SkuMoney | None = None
    status: ProductSkuStatus | None = None
    platform_sku_id: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "ProductSkuUpdate":
        required_fields = ("sku_code", "sku_name", "spec_json", "price", "status")
        for field_name in required_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductSkuRead(BaseModel):
    id: int
    product_id: int
    sku_code: str
    sku_name: str
    spec_json: dict[str, str]
    price: Decimal
    cost: Decimal | None
    status: ProductSkuStatus
    platform_sku_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductSkuListResponse(BaseModel):
    items: list[ProductSkuRead]
    total: int
    page: int
    page_size: int
