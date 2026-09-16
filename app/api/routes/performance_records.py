"""Manual performance entry, recalculation and read-only filtering APIs."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from fastapi.responses import Response
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.performance_record import (
    PerformanceRecordCreate,
    PerformanceRecordListResponse,
    PerformanceRecordRead,
    PerformanceRecordUpdate,
)
from app.schemas.performance_record_import import (
    PerformanceImportPreview,
    PerformanceImportResult,
)
from app.importers.performance_record_file_parser import MAX_IMPORT_FILE_BYTES
from app.importers.performance_record_template import build_performance_record_template
from app.services.performance_record_import_service import (
    PerformanceRecordImportService,
)
from app.services.performance_record_service import PerformanceRecordService


router = APIRouter(tags=["performance-records"])


@router.get("/workspace/templates/performance-records")
def download_performance_record_template(_: CurrentUser) -> Response:
    return Response(
        content=build_performance_record_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                'attachment; filename="performance-records-template.xlsx"'
            )
        },
    )


@router.post(
    "/products/{product_id}/performance-records/import/preview",
    response_model=PerformanceImportPreview,
)
async def preview_performance_record_import(
    product_id: Annotated[int, Path(gt=0)],
    file: Annotated[UploadFile, File(...)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> PerformanceImportPreview:
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    return PerformanceRecordImportService(db).preview(
        product_id, file.filename, content
    )


@router.post(
    "/products/{product_id}/performance-records/import",
    response_model=PerformanceImportResult,
)
async def import_performance_records(
    product_id: Annotated[int, Path(gt=0)],
    file: Annotated[UploadFile, File(...)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> PerformanceImportResult:
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    return PerformanceRecordImportService(db).import_rows(
        product_id, file.filename, content
    )


@router.post(
    "/products/{product_id}/performance-records",
    response_model=PerformanceRecordRead,
    status_code=201,
)
def create_performance_record(
    product_id: Annotated[int, Path(gt=0)],
    payload: PerformanceRecordCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> PerformanceRecordRead:
    return PerformanceRecordService(db).create(product_id, payload)


@router.get(
    "/products/{product_id}/performance-records",
    response_model=PerformanceRecordListResponse,
)
def list_performance_records(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    experiment_id: Annotated[int | None, Query(gt=0)] = None,
    generated_asset_id: Annotated[int | None, Query(gt=0)] = None,
    promotion_link_id: Annotated[int | None, Query(gt=0)] = None,
    period_start_from: Annotated[AwareDatetime | None, Query()] = None,
    period_end_to: Annotated[AwareDatetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PerformanceRecordListResponse:
    items, total = PerformanceRecordService(db).list(
        product_id=product_id,
        experiment_id=experiment_id,
        generated_asset_id=generated_asset_id,
        promotion_link_id=promotion_link_id,
        period_start_from=period_start_from,
        period_end_to=period_end_to,
        page=page,
        page_size=page_size,
    )
    return PerformanceRecordListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get(
    "/products/{product_id}/performance-records/{record_id}",
    response_model=PerformanceRecordRead,
)
def get_performance_record(
    product_id: Annotated[int, Path(gt=0)],
    record_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PerformanceRecordRead:
    return PerformanceRecordService(db).get(product_id, record_id)


@router.patch(
    "/products/{product_id}/performance-records/{record_id}",
    response_model=PerformanceRecordRead,
)
def update_performance_record(
    product_id: Annotated[int, Path(gt=0)],
    record_id: Annotated[int, Path(gt=0)],
    payload: PerformanceRecordUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> PerformanceRecordRead:
    return PerformanceRecordService(db).update(product_id, record_id, payload)
