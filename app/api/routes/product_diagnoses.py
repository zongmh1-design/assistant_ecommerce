"""Structured product diagnosis endpoints for Phase 4A."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProvider
from app.api.dependencies.auth import CurrentUser, require_write_access
from app.core.database import get_db
from app.models.user import User
from app.schemas.product_diagnosis import (
    ProductDiagnosisListResponse,
    ProductDiagnosisRead,
    ProductDiagnosisUpdate,
)
from app.services.product_diagnosis_service import ProductDiagnosisService


router = APIRouter(tags=["product-diagnoses"])
ProviderDependency = Annotated[LLMProvider, Depends(get_llm_provider)]


@router.post(
    "/products/{product_id}/diagnoses/generate",
    response_model=ProductDiagnosisRead,
    status_code=201,
)
def generate_product_diagnosis(
    product_id: Annotated[int, Path(gt=0)],
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
    provider: ProviderDependency,
) -> ProductDiagnosisRead:
    return ProductDiagnosisService(db).generate(product_id, provider)


@router.get(
    "/products/{product_id}/diagnoses",
    response_model=ProductDiagnosisListResponse,
)
def list_product_diagnoses(
    product_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductDiagnosisListResponse:
    items, total = ProductDiagnosisService(db).list(
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
    return ProductDiagnosisListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_id}/diagnoses/{diagnosis_id}",
    response_model=ProductDiagnosisRead,
)
def get_product_diagnosis(
    product_id: Annotated[int, Path(gt=0)],
    diagnosis_id: Annotated[int, Path(gt=0)],
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ProductDiagnosisRead:
    return ProductDiagnosisService(db).get(product_id, diagnosis_id)


@router.patch(
    "/products/{product_id}/diagnoses/{diagnosis_id}",
    response_model=ProductDiagnosisRead,
)
def update_product_diagnosis(
    product_id: Annotated[int, Path(gt=0)],
    diagnosis_id: Annotated[int, Path(gt=0)],
    payload: ProductDiagnosisUpdate,
    _: Annotated[User, Depends(require_write_access)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductDiagnosisRead:
    return ProductDiagnosisService(db).update(
        product_id,
        diagnosis_id,
        payload,
    )
