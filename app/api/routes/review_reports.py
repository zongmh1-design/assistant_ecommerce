"""Generate, edit and query historical operating review reports."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.review_report import (
    ReviewReportGenerate, ReviewReportListResponse, ReviewReportRead, ReviewReportUpdate,
)
from app.services.review_report_service import ReviewReportService


router = APIRouter(tags=["review-reports"])


@router.post(
    "/products/{product_id}/review-reports/generate",
    response_model=ReviewReportRead,
)
def generate_review_report(
    product_id: Annotated[int, Path(gt=0)], payload: ReviewReportGenerate,
    _: Annotated[User, Depends(require_write_access)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewReportRead:
    return ReviewReportService(db).generate(product_id, payload, provider)


@router.get(
    "/products/{product_id}/review-reports",
    response_model=ReviewReportListResponse,
)
def list_review_reports(
    product_id: Annotated[int, Path(gt=0)], _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    period_start_from: Annotated[datetime | None, Query()] = None,
    period_end_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReviewReportListResponse:
    items, total = ReviewReportService(db).list(
        product_id=product_id, period_start_from=period_start_from,
        period_end_to=period_end_to, page=page, page_size=page_size,
    )
    return ReviewReportListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/products/{product_id}/review-reports/{report_id}",
    response_model=ReviewReportRead,
)
def get_review_report(
    product_id: Annotated[int, Path(gt=0)], report_id: Annotated[int, Path(gt=0)],
    _: CurrentUser, db: Annotated[Session, Depends(get_db)],
) -> ReviewReportRead:
    return ReviewReportService(db).get(product_id, report_id)


@router.patch(
    "/products/{product_id}/review-reports/{report_id}",
    response_model=ReviewReportRead,
)
def update_review_report(
    product_id: Annotated[int, Path(gt=0)], report_id: Annotated[int, Path(gt=0)],
    payload: ReviewReportUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewReportRead:
    return ReviewReportService(db).update(product_id, report_id, payload)
