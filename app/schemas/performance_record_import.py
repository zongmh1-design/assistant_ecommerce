"""Row-level preview and partial-import response contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class PerformanceImportError(BaseModel):
    field: str | None = None
    error_code: str
    message: str


class CalculatedMetricsPreview(BaseModel):
    ctr: str
    conversion_rate: str
    roi: str | None


class PerformancePreviewRow(BaseModel):
    row_number: int
    status: Literal["valid", "invalid"]
    normalized_data: dict[str, Any] | None = None
    calculated_metrics: CalculatedMetricsPreview | None = None
    errors: list[PerformanceImportError] = Field(default_factory=list)


class PerformanceImportPreview(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[PerformancePreviewRow]


class PerformanceImportSuccessRow(BaseModel):
    row_number: int
    performance_record_id: int


class PerformanceImportFailureRow(BaseModel):
    row_number: int
    errors: list[PerformanceImportError]


class PerformanceImportResult(BaseModel):
    total_rows: int
    success_count: int
    failure_count: int
    successes: list[PerformanceImportSuccessRow]
    failures: list[PerformanceImportFailureRow]
