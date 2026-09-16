"""Response contract for resumable, admin-only demo data initialization."""

from typing import Literal

from pydantic import BaseModel, Field


class DemoDataResponse(BaseModel):
    status: Literal["completed", "already_exists", "partial"]
    completed_steps: list[str] = Field(default_factory=list)
    failed_step: str | None = None
    error_code: str | None = None
    store_id: int | None = None
    product_id: int | None = None
    sku_ids: list[int] = Field(default_factory=list)
    selected_main_image_plan_id: int | None = None
    selected_video_plan_id: int | None = None
    image_job_id: int | None = None
    video_job_id: int | None = None
    approved_image_asset_id: int | None = None
    approved_video_asset_id: int | None = None
    promotion_link_id: int | None = None
    ad_recommendation_id: int | None = None
    ad_experiment_id: int | None = None
    performance_record_ids: list[int] = Field(default_factory=list)
    review_report_id: int | None = None
    next_entry: str | None = None
