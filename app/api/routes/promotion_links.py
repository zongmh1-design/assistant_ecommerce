"""Promotion-link suggestions, CRUD, click history and public redirect."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.promotion_link import PromotionLinkStatus
from app.models.user import User
from app.schemas.promotion_link import (
    PromotionLinkClickListResponse, PromotionLinkCreate, PromotionLinkListResponse,
    PromotionLinkRead, PromotionLinkSuggestion, PromotionLinkUpdate,
)
from app.services.promotion_link_service import PromotionLinkService


router = APIRouter(tags=["promotion-links"])


@router.post("/products/{product_id}/promotion-links/generate", response_model=PromotionLinkSuggestion)
def generate_promotion_link_suggestion(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> PromotionLinkSuggestion:
    return PromotionLinkService(db).generate_suggestion(product_id, provider)


@router.post("/products/{product_id}/promotion-links", response_model=PromotionLinkRead, status_code=201)
def create_promotion_link(
    product_id: Annotated[int, Path(gt=0)], payload: PromotionLinkCreate,
    _: Annotated[User, Depends(require_write_access)], db: Annotated[Session, Depends(get_db)],
) -> PromotionLinkRead:
    return PromotionLinkService(db).create(product_id, payload)


@router.get("/products/{product_id}/promotion-links", response_model=PromotionLinkListResponse)
def list_promotion_links(
    product_id: Annotated[int, Path(gt=0)], _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[PromotionLinkStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PromotionLinkListResponse:
    items, total = PromotionLinkService(db).list(
        product_id=product_id, status=status, page=page, page_size=page_size
    )
    return PromotionLinkListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/products/{product_id}/promotion-links/{promotion_link_id}", response_model=PromotionLinkRead)
def get_promotion_link(
    product_id: Annotated[int, Path(gt=0)], promotion_link_id: Annotated[int, Path(gt=0)],
    _: CurrentUser, db: Annotated[Session, Depends(get_db)],
) -> PromotionLinkRead:
    return PromotionLinkService(db).get(product_id, promotion_link_id)


@router.patch("/products/{product_id}/promotion-links/{promotion_link_id}", response_model=PromotionLinkRead)
def update_promotion_link(
    product_id: Annotated[int, Path(gt=0)], promotion_link_id: Annotated[int, Path(gt=0)],
    payload: PromotionLinkUpdate, _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> PromotionLinkRead:
    return PromotionLinkService(db).update(product_id, promotion_link_id, payload)


@router.get("/products/{product_id}/promotion-links/{promotion_link_id}/clicks", response_model=PromotionLinkClickListResponse)
def list_promotion_link_clicks(
    product_id: Annotated[int, Path(gt=0)], promotion_link_id: Annotated[int, Path(gt=0)],
    _: CurrentUser, db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PromotionLinkClickListResponse:
    items, total = PromotionLinkService(db).list_clicks(
        product_id=product_id, link_id=promotion_link_id, page=page, page_size=page_size
    )
    return PromotionLinkClickListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/r/{tracking_code}", response_class=RedirectResponse)
def redirect_promotion_link(
    tracking_code: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    request: Request, db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    target_url = PromotionLinkService(db).record_click(
        tracking_code,
        client_ip=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=target_url, status_code=302)
