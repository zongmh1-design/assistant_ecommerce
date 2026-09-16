"""Generate advisory-only ad recommendations and apply human decisions."""

from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.ad_recommendation_context import build_ad_recommendation_context
from app.ai.llm_provider import (
    InvalidLLMOutputError, LLMAuthenticationError, LLMConfigurationError,
    LLMProvider, LLMProviderError, LLMRateLimitError, LLMTimeoutError,
    StructuredLLMResult,
)
from app.ai.prompts.ad_recommendation import (
    AD_RECOMMENDATION_SYSTEM_PROMPT, build_ad_recommendation_user_prompt,
)
from app.core.exceptions import AppError
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.product import Product
from app.repositories.ad_recommendation_repository import AdRecommendationRepository
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.product_diagnosis_repository import ProductDiagnosisRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_link_repository import PromotionLinkRepository
from app.schemas.ad_recommendation import (
    AdRecommendationConfirmation, AdRecommendationOutput, AdRecommendationUpdate,
)


class AdRecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.diagnoses = ProductDiagnosisRepository(db)
        self.plans = CreativePlanRepository(db)
        self.assets = GeneratedAssetRepository(db)
        self.links = PromotionLinkRepository(db)
        self.recommendations = AdRecommendationRepository(db)

    def generate(self, product_id: int, provider: LLMProvider) -> AdRecommendation:
        product = self._require_product(product_id)
        context = build_ad_recommendation_context(
            product,
            self.diagnoses.get_latest_by_product(product_id),
            self.plans.list_selected_for_ad_context(product_id),
            self.assets.list_approved_for_ad_context(product_id),
            self.links.list_active_for_ad_context(product_id),
        )
        result = self._call_provider(
            provider,
            build_ad_recommendation_user_prompt(context),
        )
        output = _validate_output(result)
        recommendation = AdRecommendation(
            product_id=product_id,
            summary_text=output.summary,
            objective_text=output.objective,
            audience_segments_json=_json(output.audience_segments),
            budget_plan_json=output.budget_plan.model_dump(mode="json"),
            creative_tests_json=_json(output.creative_tests),
            bid_strategy_json=output.bid_strategy.model_dump(mode="json"),
            risk_controls_json=_json(output.risk_controls),
            next_steps_json=output.next_steps,
            confirm_status=AdRecommendationConfirmStatus.PENDING,
            provider_name=result.provider_name,
            model_name=result.model_name,
            usage_json=result.usage,
            input_context_json=context.model_dump(mode="json"),
        )
        self.recommendations.add(recommendation)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(recommendation)
        return recommendation

    def list(
        self, *, product_id: int,
        confirm_status: AdRecommendationConfirmStatus | None,
        page: int, page_size: int,
    ) -> tuple[list[AdRecommendation], int]:
        self._require_product(product_id)
        return self.recommendations.list_by_product(
            product_id=product_id, confirm_status=confirm_status,
            offset=(page - 1) * page_size, limit=page_size,
        )

    def get(self, product_id: int, recommendation_id: int) -> AdRecommendation:
        self._require_product(product_id)
        recommendation = self.recommendations.get_by_id_and_product_id(
            recommendation_id, product_id
        )
        if recommendation is None:
            raise _not_found(recommendation_id)
        return recommendation

    def update(
        self, product_id: int, recommendation_id: int, payload: AdRecommendationUpdate
    ) -> AdRecommendation:
        self._require_product(product_id)
        recommendation = self.recommendations.get_for_update_by_id_and_product_id(
            recommendation_id, product_id
        )
        if recommendation is None:
            raise _not_found(recommendation_id)
        if recommendation.confirm_status != AdRecommendationConfirmStatus.PENDING:
            self.db.rollback()
            raise AppError(
                status_code=409, code="ad_recommendation_frozen",
                message="Confirmed or rejected recommendations cannot be edited",
            )
        self.recommendations.update(
            recommendation, payload.model_dump(mode="json", exclude_unset=True)
        )
        return self._commit_and_refresh(recommendation)

    def confirm(
        self, product_id: int, recommendation_id: int,
        payload: AdRecommendationConfirmation, current_user_id: int,
    ) -> AdRecommendation:
        self._require_product(product_id)
        recommendation = self.recommendations.get_for_update_by_id_and_product_id(
            recommendation_id, product_id
        )
        if recommendation is None:
            raise _not_found(recommendation_id)
        if recommendation.confirm_status != AdRecommendationConfirmStatus.PENDING:
            self.db.rollback()
            raise AppError(
                status_code=409, code="ad_recommendation_already_decided",
                message="The recommendation already has a final human decision",
            )
        self.recommendations.update(
            recommendation,
            {
                "confirm_status": payload.confirm_status,
                "confirmed_by": current_user_id,
                "confirmed_at": datetime.now(timezone.utc),
                "confirm_remark": payload.confirm_remark,
            },
        )
        return self._commit_and_refresh(recommendation)

    def get_latest_confirmed_for_product(self, product_id: int) -> AdRecommendation | None:
        self._require_product(product_id)
        return self.recommendations.get_latest_confirmed_for_product(product_id)

    def _call_provider(self, provider: LLMProvider, user_prompt: str) -> StructuredLLMResult:
        try:
            return provider.generate_structured(
                system_prompt=AD_RECOMMENDATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=AdRecommendationOutput,
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
            raise _invalid_output() from exc
        except LLMProviderError as exc:
            raise _provider_error(502, "llm_provider_error", "Ad recommendation provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Ad recommendation provider call failed unexpectedly") from exc

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404, code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def _commit_and_refresh(self, recommendation: AdRecommendation) -> AdRecommendation:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(recommendation)
        return recommendation


def _json(items: list[object]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in items]


def _validate_output(result: StructuredLLMResult) -> AdRecommendationOutput:
    try:
        if not result.raw_output.strip():
            raise ValueError("raw_output is empty")
        return AdRecommendationOutput.model_validate(result.data)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise _invalid_output() from exc


def _not_found(recommendation_id: int) -> AppError:
    return AppError(
        status_code=404, code="ad_recommendation_not_found",
        message=f"Ad recommendation {recommendation_id} was not found",
    )


def _invalid_output() -> AppError:
    return AppError(
        status_code=502, code="invalid_llm_output",
        message="Ad recommendation provider returned invalid structured output",
    )


def _provider_error(status_code: int, code: str, message: str) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
