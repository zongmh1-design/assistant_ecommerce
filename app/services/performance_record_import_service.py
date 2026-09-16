"""Stateless preview and row-isolated import for performance record files."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.importers.performance_record_file_parser import (
    ParsedPerformanceRow,
    PerformanceRecordFileParser,
)
from app.schemas.performance_record import PerformanceRecordCreate
from app.schemas.performance_record_import import (
    CalculatedMetricsPreview,
    PerformanceImportError,
    PerformanceImportFailureRow,
    PerformanceImportPreview,
    PerformanceImportResult,
    PerformanceImportSuccessRow,
    PerformancePreviewRow,
)
from app.services.performance_record_service import PerformanceRecordService


class PerformanceRecordImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.parser = PerformanceRecordFileParser()
        self.performance_records = PerformanceRecordService(db)

    def preview(
        self, product_id: int, filename: str | None, content: bytes
    ) -> PerformanceImportPreview:
        self.performance_records.require_product_exists(product_id)
        parsed_rows = self.parser.parse(filename, content)
        result_rows: list[PerformancePreviewRow] = []
        valid_count = 0
        for row in parsed_rows:
            if row.errors:
                result_rows.append(_invalid_preview(row, _parse_errors(row)))
                continue
            try:
                payload = PerformanceRecordCreate.model_validate(row.data)
                prepared = self.performance_records.validate_and_prepare(
                    product_id, payload
                )
            except ValidationError as exc:
                result_rows.append(
                    _invalid_preview(row, _validation_errors(exc))
                )
                continue
            except AppError as exc:
                result_rows.append(_invalid_preview(row, [_app_error(exc)]))
                continue
            valid_count += 1
            result_rows.append(
                PerformancePreviewRow(
                    row_number=row.row_number,
                    status="valid",
                    normalized_data=payload.model_dump(mode="json"),
                    calculated_metrics=CalculatedMetricsPreview(
                        ctr=str(prepared.metrics.ctr),
                        conversion_rate=str(prepared.metrics.conversion_rate),
                        roi=(
                            str(prepared.metrics.roi)
                            if prepared.metrics.roi is not None else None
                        ),
                    ),
                )
            )
        return PerformanceImportPreview(
            total_rows=len(parsed_rows),
            valid_rows=valid_count,
            invalid_rows=len(parsed_rows) - valid_count,
            rows=result_rows,
        )

    def import_rows(
        self, product_id: int, filename: str | None, content: bytes
    ) -> PerformanceImportResult:
        self.performance_records.require_product_exists(product_id)
        parsed_rows = self.parser.parse(filename, content)
        successes: list[PerformanceImportSuccessRow] = []
        failures: list[PerformanceImportFailureRow] = []
        for row in parsed_rows:
            if row.errors:
                failures.append(
                    PerformanceImportFailureRow(
                        row_number=row.row_number, errors=_parse_errors(row)
                    )
                )
                continue
            try:
                payload = PerformanceRecordCreate.model_validate(row.data)
                # create() revalidates current relations/status and commits this row only.
                record = self.performance_records.create(product_id, payload)
            except ValidationError as exc:
                failures.append(
                    PerformanceImportFailureRow(
                        row_number=row.row_number,
                        errors=_validation_errors(exc),
                    )
                )
            except AppError as exc:
                self.db.rollback()
                failures.append(
                    PerformanceImportFailureRow(
                        row_number=row.row_number, errors=[_app_error(exc)]
                    )
                )
            except Exception:
                self.db.rollback()
                failures.append(
                    PerformanceImportFailureRow(
                        row_number=row.row_number,
                        errors=[PerformanceImportError(
                            field=None,
                            error_code="import_row_persistence_error",
                            message="The row could not be saved",
                        )],
                    )
                )
            else:
                successes.append(
                    PerformanceImportSuccessRow(
                        row_number=row.row_number,
                        performance_record_id=record.id,
                    )
                )
        return PerformanceImportResult(
            total_rows=len(parsed_rows),
            success_count=len(successes),
            failure_count=len(failures),
            successes=successes,
            failures=failures,
        )


def _invalid_preview(
    row: ParsedPerformanceRow, errors: list[PerformanceImportError]
) -> PerformancePreviewRow:
    return PerformancePreviewRow(
        row_number=row.row_number, status="invalid", errors=errors
    )


def _parse_errors(row: ParsedPerformanceRow) -> list[PerformanceImportError]:
    return [
        PerformanceImportError(
            field=issue.field,
            error_code=issue.error_code,
            message=issue.message,
        )
        for issue in row.errors
    ]


def _validation_errors(exc: ValidationError) -> list[PerformanceImportError]:
    errors: list[PerformanceImportError] = []
    for item in exc.errors(include_url=False):
        location = item.get("loc", ())
        field = str(location[-1]) if location else None
        message = str(item.get("msg", "Invalid value"))
        errors.append(
            PerformanceImportError(
                field=field,
                error_code=_validation_code(field, message),
                message=message,
            )
        )
    return errors


def _validation_code(field: str | None, message: str) -> str:
    lowered = message.lower()
    if "period_end must be later" in lowered:
        return "invalid_period"
    if "clicks cannot exceed impressions" in lowered:
        return "clicks_exceed_impressions"
    if "conversions cannot exceed clicks" in lowered:
        return "conversions_exceed_clicks"
    return f"invalid_{field}" if field else "invalid_row"


def _app_error(exc: AppError) -> PerformanceImportError:
    field_by_code = {
        "creative_plan_not_found": "creative_plan_id",
        "generated_asset_not_found": "generated_asset_id",
        "promotion_link_not_found": "promotion_link_id",
        "ad_experiment_not_found": "experiment_id",
        "ad_experiment_not_started": "experiment_id",
        "invalid_performance_record": None,
    }
    return PerformanceImportError(
        field=field_by_code.get(exc.code),
        error_code=exc.code,
        message=exc.message,
    )
