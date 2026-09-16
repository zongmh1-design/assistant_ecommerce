"""API schemas for generation jobs, results and event timelines."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.generation_job import (
    GenerationJobEventType,
    GenerationJobKind,
    GenerationJobStatus,
)


class MediaGenerationInput(BaseModel):
    job_id: int
    title: str
    content_json: dict[str, Any]
    rationale_text: str


class ImageGenerationResult(BaseModel):
    asset_type: Literal["image"]
    mock: bool
    url: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    generator: str = Field(min_length=1)
    model_name: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")


class VideoGenerationResult(BaseModel):
    asset_type: Literal["video"]
    mock: bool
    url: str = Field(min_length=1)
    duration_sec: int = Field(gt=0)
    generator: str = Field(min_length=1)
    model_name: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")


class GenerationJobEventRead(BaseModel):
    id: int
    job_id: int
    event_type: GenerationJobEventType
    event_message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerationJobRead(BaseModel):
    id: int
    product_id: int
    creative_plan_id: int
    job_kind: GenerationJobKind
    job_status: GenerationJobStatus
    attempts: int
    max_attempts: int
    locked_at: datetime | None
    locked_by: str | None
    next_run_at: datetime | None
    result_json: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerationJobDetail(GenerationJobRead):
    events: list[GenerationJobEventRead]


class GenerationJobListResponse(BaseModel):
    items: list[GenerationJobRead]
    total: int
    page: int
    page_size: int


class TimeoutSweepResponse(BaseModel):
    timed_out_count: int
    job_ids: list[int]
