"""Create, update, read and paginated response schemas for Store."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.store import Platform


class StoreCreate(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    platform: Platform
    external_store_id: str | None = Field(default=None, max_length=100)
    owner_name: str | None = Field(default=None, max_length=100)
    remark: str | None = None


class StoreUpdate(BaseModel):
    store_name: str | None = Field(default=None, min_length=1, max_length=100)
    platform: Platform | None = None
    external_store_id: str | None = Field(default=None, max_length=100)
    owner_name: str | None = Field(default=None, max_length=100)
    remark: str | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "StoreUpdate":
        for field_name in ("store_name", "platform"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class StoreRead(BaseModel):
    id: int
    store_name: str
    platform: Platform
    external_store_id: str | None
    owner_name: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreListResponse(BaseModel):
    items: list[StoreRead]
    total: int
    page: int
    page_size: int
