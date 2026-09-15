"""Competitor and public-link parsing REST endpoints for Phase 3A."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.integrations.mock_public_link_parser import MockPublicLinkParser
from app.integrations.public_link_parser import PublicLinkParser
from app.models.user import User
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorRead,
    CompetitorUpdate,
    PublicLinkParseTaskCreate,
    PublicLinkParseTaskRead,
)
from app.services.competitor_service import CompetitorService
from app.services.public_link_parse_service import PublicLinkParseService


router = APIRouter(tags=["competitors"])


def get_public_link_parser() -> PublicLinkParser:
    """Application composition point; replace this dependency for a legal real parser."""
    return MockPublicLinkParser()


ParserDependency = Annotated[PublicLinkParser, Depends(get_public_link_parser)]


@router.post(
    "/products/{product_id}/competitors",
    response_model=CompetitorRead,
    status_code=201,
)
def create_competitor(
    product_id: Annotated[int, Path(gt=0)],
    payload: CompetitorCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> CompetitorRead:
    return CompetitorService(db).create(product_id, payload)


@router.get(
    "/products/{product_id}/competitors",
    response_model=CompetitorListResponse,
)
def list_competitors(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CompetitorListResponse:
    items, total = CompetitorService(db).list(
        product_id=product_id, page=page, page_size=page_size
    )
    return CompetitorListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/competitors/{competitor_id}", response_model=CompetitorRead)
def get_competitor(
    competitor_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitorRead:
    return CompetitorService(db).get(competitor_id)


@router.patch("/competitors/{competitor_id}", response_model=CompetitorRead)
def update_competitor(
    competitor_id: Annotated[int, Path(gt=0)],
    payload: CompetitorUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> CompetitorRead:
    return CompetitorService(db).update(competitor_id, payload)


@router.post(
    "/products/{product_id}/competitors/import-url-tasks",
    response_model=PublicLinkParseTaskRead,
    status_code=201,
)
def create_link_parse_task(
    product_id: Annotated[int, Path(gt=0)],
    payload: PublicLinkParseTaskCreate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    parser: ParserDependency,
) -> PublicLinkParseTaskRead:
    return PublicLinkParseService(db, parser).create_task(product_id, payload)


@router.get(
    "/products/{product_id}/link-parse-tasks/{task_id}",
    response_model=PublicLinkParseTaskRead,
)
def get_link_parse_task(
    product_id: Annotated[int, Path(gt=0)],
    task_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    parser: ParserDependency,
) -> PublicLinkParseTaskRead:
    return PublicLinkParseService(db, parser).get_task(product_id, task_id)


@router.post(
    "/products/{product_id}/link-parse-tasks/{task_id}/run",
    response_model=PublicLinkParseTaskRead,
)
def run_link_parse_task(
    product_id: Annotated[int, Path(gt=0)],
    task_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    parser: ParserDependency,
) -> PublicLinkParseTaskRead:
    return PublicLinkParseService(db, parser).run_task(product_id, task_id)


@router.post(
    "/products/{product_id}/link-parse-tasks/{task_id}/confirm",
    response_model=CompetitorRead,
    status_code=201,
)
def confirm_link_parse_task(
    product_id: Annotated[int, Path(gt=0)],
    task_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    parser: ParserDependency,
) -> CompetitorRead:
    return PublicLinkParseService(db, parser).confirm(product_id, task_id)
