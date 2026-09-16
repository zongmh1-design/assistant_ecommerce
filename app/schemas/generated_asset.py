"""Strict asset sync, query and human-review schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.generated_asset import AssetReviewStatus, GeneratedAssetType


class GeneratedAssetUpdate(BaseModel):
    review_status: AssetReviewStatus | None = None
    usage_scene: str | None = Field(default=None, max_length=200)
    score: int | None = Field(default=None, strict=True, ge=0, le=100)
    tags_json: list[str] | None = None
    remark: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("tags_json", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> object:
        if value is None:
            return value
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Each tag must be a string")
            tag = item.strip()
            if tag and tag not in seen:
                normalized.append(tag)
                seen.add(tag)
        return normalized

    @model_validator(mode="after")
    def reject_required_nulls(self) -> "GeneratedAssetUpdate":
        for field_name in ("review_status", "tags_json"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class GeneratedAssetRead(BaseModel):
    id: int
    product_id: int
    creative_plan_id: int
    generation_job_id: int
    asset_type: GeneratedAssetType
    asset_url: str
    model_name: str
    width: int | None
    height: int | None
    duration_sec: int | None
    review_status: AssetReviewStatus
    version_no: int
    usage_scene: str | None
    score: int | None
    tags_json: list[str]
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratedAssetListResponse(BaseModel):
    items: list[GeneratedAssetRead]
    total: int
    page: int
    page_size: int


class AssetSyncFailure(BaseModel):
    job_id: int
    code: str
    message: str


class AssetSyncResult(BaseModel):
    synced_count: int
    skipped_count: int
    failed_count: int
    asset_ids: list[int]
    failures: list[AssetSyncFailure]
