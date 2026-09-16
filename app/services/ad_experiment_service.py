"""Generate and manage human-controlled experiment plans without ad execution."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.ad_experiment_context import build_ad_experiment_context
from app.ai.llm_provider import (
    InvalidLLMOutputError, LLMAuthenticationError, LLMConfigurationError,
    LLMProvider, LLMProviderError, LLMRateLimitError, LLMTimeoutError,
    StructuredLLMResult,
)
from app.ai.prompts.ad_experiment import (
    AD_EXPERIMENT_SYSTEM_PROMPT, build_ad_experiment_user_prompt,
)
from app.core.exceptions import AppError
from app.models.ad_experiment import AdExperiment, AdExperimentStatus
from app.models.ad_recommendation import AdRecommendation, AdRecommendationConfirmStatus
from app.models.generated_asset import AssetReviewStatus, GeneratedAsset
from app.models.product import Product
from app.models.promotion_link import PromotionLink, PromotionLinkStatus
from app.repositories.ad_experiment_repository import AdExperimentRepository
from app.repositories.ad_recommendation_repository import AdRecommendationRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_link_repository import PromotionLinkRepository
from app.schemas.ad_experiment import (
    AdExperimentGenerate, AdExperimentOutput, AdExperimentStatusUpdate,
    AdExperimentUpdate,
)


class AdExperimentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.recommendations = AdRecommendationRepository(db)
        self.assets = GeneratedAssetRepository(db)
        self.links = PromotionLinkRepository(db)
        self.experiments = AdExperimentRepository(db)

    def generate(
        self, product_id: int, payload: AdExperimentGenerate, provider: LLMProvider
    ) -> AdExperiment:
        product = self._require_product(product_id)
        recommendation = self._require_confirmed_recommendation(
            product_id, payload.recommendation_id
        )
        asset = self._validate_asset(product_id, payload.related_asset_id)
        link = self._validate_link(product_id, payload.related_link_id)
        context = build_ad_experiment_context(product, recommendation, asset, link)
        result = self._call_provider(
            provider, build_ad_experiment_user_prompt(context)
        )
        output = _validate_output(result)
        experiment = AdExperiment(
            product_id=product_id,
            ad_recommendation_id=recommendation.id,
            related_asset_id=asset.id if asset is not None else None,
            related_link_id=link.id if link is not None else None,
            experiment_name=output.experiment_name,
            target_text=output.target_text,
            audience_text=output.audience_text,
            budget_amount=output.budget_amount,
            success_metric_text=output.success_metric_text,
            hypothesis_text=output.hypothesis_text,
            experiment_status=AdExperimentStatus.DRAFT,
            provider_name=result.provider_name,
            model_name=result.model_name,
            usage_json=result.usage,
            input_context_json=context.model_dump(mode="json"),
        )
        self.experiments.add(experiment)
        return self._commit_and_refresh(experiment)

    def list(
        self, *, product_id: int, experiment_status: AdExperimentStatus | None,
        ad_recommendation_id: int | None, page: int, page_size: int,
    ) -> tuple[list[AdExperiment], int]:
        self._require_product(product_id)
        return self.experiments.list_by_product(
            product_id=product_id, experiment_status=experiment_status,
            ad_recommendation_id=ad_recommendation_id,
            offset=(page - 1) * page_size, limit=page_size,
        )

    def get(self, product_id: int, experiment_id: int) -> AdExperiment:
        self._require_product(product_id)
        experiment = self.experiments.get_by_id_and_product_id(
            experiment_id, product_id
        )
        if experiment is None:
            raise _not_found(experiment_id)
        return experiment

    def update(
        self, product_id: int, experiment_id: int, payload: AdExperimentUpdate
    ) -> AdExperiment:
        self._require_product(product_id)
        experiment = self.experiments.get_for_update_by_id_and_product_id(
            experiment_id, product_id
        )
        if experiment is None:
            raise _not_found(experiment_id)
        if experiment.experiment_status != AdExperimentStatus.DRAFT:
            self.db.rollback()
            raise AppError(
                status_code=409, code="ad_experiment_frozen",
                message="Only draft experiments can be edited",
            )
        changes = payload.model_dump(exclude_unset=True)
        if "related_asset_id" in changes:
            asset = self._validate_asset(product_id, changes["related_asset_id"])
            changes["related_asset_id"] = asset.id if asset is not None else None
        if "related_link_id" in changes:
            link = self._validate_link(product_id, changes["related_link_id"])
            changes["related_link_id"] = link.id if link is not None else None
        self.experiments.update(experiment, changes)
        return self._commit_and_refresh(experiment)

    def update_status(
        self, product_id: int, experiment_id: int,
        payload: AdExperimentStatusUpdate,
    ) -> AdExperiment:
        self._require_product(product_id)
        experiment = self.experiments.get_for_update_by_id_and_product_id(
            experiment_id, product_id
        )
        if experiment is None:
            raise _not_found(experiment_id)
        _validate_status_transition(
            experiment.experiment_status, payload.experiment_status
        )
        experiment.experiment_status = payload.experiment_status
        return self._commit_and_refresh(experiment)

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404, code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def _require_confirmed_recommendation(
        self, product_id: int, recommendation_id: int
    ) -> AdRecommendation:
        recommendation = self.recommendations.get_by_id_and_product_id(
            recommendation_id, product_id
        )
        if recommendation is None:
            raise AppError(
                status_code=404, code="ad_recommendation_not_found",
                message=f"Ad recommendation {recommendation_id} was not found",
            )
        if recommendation.confirm_status != AdRecommendationConfirmStatus.CONFIRMED:
            raise AppError(
                status_code=409, code="ad_recommendation_not_confirmed",
                message="Only confirmed recommendations can create experiments",
            )
        return recommendation

    def _validate_asset(
        self, product_id: int, asset_id: int | None
    ) -> GeneratedAsset | None:
        if asset_id is None:
            return None
        asset = self.assets.get_by_id_and_product_id(asset_id, product_id)
        if asset is None:
            raise AppError(
                status_code=404, code="generated_asset_not_found",
                message=f"Generated asset {asset_id} was not found",
            )
        if asset.review_status != AssetReviewStatus.APPROVED:
            raise AppError(
                status_code=409, code="generated_asset_not_approved",
                message="Only approved assets can be attached to an experiment",
            )
        return asset

    def _validate_link(
        self, product_id: int, link_id: int | None
    ) -> PromotionLink | None:
        if link_id is None:
            return None
        link = self.links.get_by_id_and_product_id(link_id, product_id)
        if link is None:
            raise AppError(
                status_code=404, code="promotion_link_not_found",
                message=f"Promotion link {link_id} was not found",
            )
        if link.status != PromotionLinkStatus.ACTIVE:
            raise AppError(
                status_code=409, code="promotion_link_inactive",
                message="Only active promotion links can be attached to an experiment",
            )
        return link

    def _call_provider(self, provider: LLMProvider, user_prompt: str) -> StructuredLLMResult:
        try:
            return provider.generate_structured(
                system_prompt=AD_EXPERIMENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=AdExperimentOutput,
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
            raise _provider_error(502, "llm_provider_error", "Ad experiment provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Ad experiment provider call failed unexpectedly") from exc

    def _commit_and_refresh(self, experiment: AdExperiment) -> AdExperiment:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(experiment)
        return experiment


def _validate_output(result: StructuredLLMResult) -> AdExperimentOutput:
    try:
        if not result.raw_output.strip():
            raise ValueError("raw_output is empty")
        return AdExperimentOutput.model_validate(result.data)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise _invalid_output() from exc


def _validate_status_transition(
    current: AdExperimentStatus, desired: AdExperimentStatus
) -> None:
    allowed = {
        AdExperimentStatus.DRAFT: {
            AdExperimentStatus.CONFIRMED, AdExperimentStatus.CANCELLED,
        },
        AdExperimentStatus.CONFIRMED: {
            AdExperimentStatus.RUNNING, AdExperimentStatus.CANCELLED,
        },
        AdExperimentStatus.RUNNING: {
            AdExperimentStatus.FINISHED, AdExperimentStatus.CANCELLED,
        },
        AdExperimentStatus.FINISHED: set(),
        AdExperimentStatus.CANCELLED: set(),
    }
    if desired not in allowed[current]:
        raise AppError(
            status_code=409, code="invalid_ad_experiment_status_transition",
            message=f"Cannot change experiment from {current.value} to {desired.value}",
        )


def _not_found(experiment_id: int) -> AppError:
    return AppError(
        status_code=404, code="ad_experiment_not_found",
        message=f"Ad experiment {experiment_id} was not found",
    )


def _invalid_output() -> AppError:
    return AppError(
        status_code=502, code="invalid_llm_output",
        message="Ad experiment provider returned invalid structured output",
    )


def _provider_error(status_code: int, code: str, message: str) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
