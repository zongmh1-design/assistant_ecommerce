"""Product diagnosis generation, history queries and human editing."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.llm_provider import (
    InvalidLLMOutputError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredLLMResult,
)
from app.ai.product_diagnosis_context import build_product_diagnosis_context
from app.ai.prompts.product_diagnosis import (
    PRODUCT_DIAGNOSIS_SYSTEM_PROMPT,
    build_product_diagnosis_user_prompt,
)
from app.core.exceptions import AppError
from app.models.product import Product
from app.models.product_diagnosis import ProductDiagnosis
from app.repositories.competitor_repository import CompetitorRepository
from app.repositories.product_diagnosis_repository import ProductDiagnosisRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product_diagnosis import ProductDiagnosisOutput, ProductDiagnosisUpdate


class ProductDiagnosisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.competitors = CompetitorRepository(db)
        self.diagnoses = ProductDiagnosisRepository(db)

    def generate(
        self, product_id: int, provider: LLMProvider
    ) -> ProductDiagnosis:
        product = self._require_product(product_id)
        competitors = self.competitors.list_for_diagnosis(product_id)
        context = build_product_diagnosis_context(product, competitors)
        user_prompt = build_product_diagnosis_user_prompt(context)

        try:
            provider_result = provider.generate_structured(
                system_prompt=PRODUCT_DIAGNOSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=ProductDiagnosisOutput,
            )
        except LLMConfigurationError as exc:
            raise _provider_error(503, "llm_configuration_error", "LLM provider is not configured") from exc
        except LLMAuthenticationError as exc:
            raise _provider_error(502, "llm_authentication_error", "LLM provider rejected authentication") from exc
        except LLMRateLimitError as exc:
            raise _provider_error(503, "llm_rate_limit_error", "LLM provider rate limit was reached") from exc
        except LLMTimeoutError as exc:
            raise _provider_error(504, "llm_timeout_error", "LLM provider request timed out") from exc
        except InvalidLLMOutputError as exc:
            raise _provider_error(502, "invalid_llm_output", "LLM provider returned invalid structured output") from exc
        except LLMProviderError as exc:
            raise _provider_error(502, "llm_provider_error", "Product diagnosis provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Product diagnosis provider call failed unexpectedly") from exc

        output = _validate_provider_result(provider_result)
        diagnosis = ProductDiagnosis(
            product_id=product.id,
            source_type=provider_result.source_type,
            provider_name=provider_result.provider_name,
            model_name=provider_result.model_name,
            usage_json=provider_result.usage,
            input_context_json=context.model_dump(mode="json"),
            raw_output=provider_result.raw_output,
            **output.model_dump(),
        )
        self.diagnoses.add(diagnosis)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(diagnosis)
        return diagnosis

    def list(
        self, *, product_id: int, page: int, page_size: int
    ) -> tuple[list[ProductDiagnosis], int]:
        self._require_product(product_id)
        return self.diagnoses.list_by_product(
            product_id=product_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, diagnosis_id: int) -> ProductDiagnosis:
        self._require_product(product_id)
        diagnosis = self.diagnoses.get_by_id_and_product_id(
            diagnosis_id, product_id
        )
        if diagnosis is None:
            raise AppError(
                status_code=404,
                code="product_diagnosis_not_found",
                message=f"Product diagnosis {diagnosis_id} was not found for product {product_id}",
            )
        return diagnosis

    def update(
        self,
        product_id: int,
        diagnosis_id: int,
        payload: ProductDiagnosisUpdate,
    ) -> ProductDiagnosis:
        diagnosis = self.get(product_id, diagnosis_id)
        self.diagnoses.update(
            diagnosis,
            payload.model_dump(exclude_unset=True),
        )
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product


def _validate_provider_result(
    provider_result: StructuredLLMResult,
) -> ProductDiagnosisOutput:
    try:
        if not provider_result.source_type.strip():
            raise ValueError("source_type is empty")
        if not provider_result.raw_output.strip():
            raise ValueError("raw_output is empty")
        return ProductDiagnosisOutput.model_validate(provider_result.data)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise AppError(
            status_code=502,
            code="invalid_llm_output",
            message="Product diagnosis provider returned invalid structured output",
        ) from exc


def _provider_error(
    status_code: int,
    code: str,
    message: str,
) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
