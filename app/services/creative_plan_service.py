"""Generate, query, edit and select unified creative plans."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.creative_plan_context import build_creative_plan_context
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
from app.ai.prompts.main_image_plan import (
    MAIN_IMAGE_PLAN_SYSTEM_PROMPT,
    build_main_image_plan_user_prompt,
)
from app.ai.prompts.video_script import (
    VIDEO_SCRIPT_SYSTEM_PROMPT,
    build_video_script_user_prompt,
)
from app.core.exceptions import AppError
from app.models.creative_plan import CreativePlan, CreativePlanStatus, CreativePlanType
from app.models.product import Product
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.product_diagnosis_repository import ProductDiagnosisRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.creative_plan import (
    CreativePlanContext,
    CreativePlanUpdate,
    MainImagePlanContent,
    MainImagePlansOutput,
    VideoScriptContent,
    VideoScriptsOutput,
)


class CreativePlanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.diagnoses = ProductDiagnosisRepository(db)
        self.plans = CreativePlanRepository(db)

    def generate_main_images(
        self, product_id: int, provider: LLMProvider
    ) -> list[CreativePlan]:
        context = self._build_context(product_id)
        result, output = self._generate_structured(
            provider=provider,
            system_prompt=MAIN_IMAGE_PLAN_SYSTEM_PROMPT,
            user_prompt=build_main_image_plan_user_prompt(context),
            response_schema=MainImagePlansOutput,
        )
        plans = [
            self._new_plan(
                product_id=product_id,
                plan_type=CreativePlanType.MAIN_IMAGE,
                title=item.title,
                content=MainImagePlanContent(
                    visual_structure=item.visual_structure,
                    core_copy=item.core_copy,
                    highlighted_selling_points=item.highlighted_selling_points,
                ).model_dump(mode="json"),
                rationale=item.rationale,
                context=context,
                provider_result=result,
            )
            for item in output.plans
        ]
        return self._save_generated_batch(plans)

    def generate_video_scripts(
        self, product_id: int, provider: LLMProvider
    ) -> list[CreativePlan]:
        context = self._build_context(product_id)
        result, output = self._generate_structured(
            provider=provider,
            system_prompt=VIDEO_SCRIPT_SYSTEM_PROMPT,
            user_prompt=build_video_script_user_prompt(context),
            response_schema=VideoScriptsOutput,
        )
        plans = [
            self._new_plan(
                product_id=product_id,
                plan_type=CreativePlanType.VIDEO_SCRIPT,
                title=item.title,
                content=VideoScriptContent(
                    opening_hook=item.opening_hook,
                    storyboard=item.storyboard,
                    voiceover=item.voiceover,
                    conversion_cta=item.conversion_cta,
                ).model_dump(mode="json"),
                rationale=item.rationale,
                context=context,
                provider_result=result,
            )
            for item in output.scripts
        ]
        return self._save_generated_batch(plans)

    def list(
        self,
        *,
        product_id: int,
        plan_type: CreativePlanType | None,
        status: CreativePlanStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CreativePlan], int]:
        self._require_product(product_id)
        return self.plans.list_by_product(
            product_id=product_id,
            plan_type=plan_type,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, product_id: int, plan_id: int) -> CreativePlan:
        self._require_product(product_id)
        plan = self.plans.get_by_id_and_product_id(plan_id, product_id)
        if plan is None:
            raise AppError(
                status_code=404,
                code="creative_plan_not_found",
                message=f"Creative plan {plan_id} was not found for product {product_id}",
            )
        return plan

    def update(
        self,
        product_id: int,
        plan_id: int,
        payload: CreativePlanUpdate,
    ) -> CreativePlan:
        plan = self.get(product_id, plan_id)
        changes = payload.model_dump(exclude_unset=True)
        if "content_json" in changes:
            changes["content_json"] = _validate_content(
                plan.plan_type, changes["content_json"]
            )
        desired_status = changes.get("status")
        if desired_status is not None and desired_status != plan.status:
            _validate_status_transition(plan.status, desired_status)
            if desired_status == CreativePlanStatus.SELECTED:
                self.plans.archive_selected(
                    product_id=plan.product_id,
                    plan_type=plan.plan_type,
                    exclude_plan_id=plan.id,
                )
        self.plans.update(plan, changes)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="creative_plan_selection_conflict",
                message="Another plan of this type is already selected",
            ) from exc
        self.db.refresh(plan)
        return plan

    def _build_context(self, product_id: int) -> CreativePlanContext:
        product = self._require_product(product_id)
        diagnosis = self.diagnoses.get_latest_by_product(product_id)
        return build_creative_plan_context(product, diagnosis)

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product

    def _generate_structured(
        self,
        *,
        provider: LLMProvider,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> tuple[StructuredLLMResult, MainImagePlansOutput | VideoScriptsOutput]:
        try:
            result = provider.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
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
            raise _invalid_output_error() from exc
        except LLMProviderError as exc:
            raise _provider_error(502, "llm_provider_error", "Creative plan provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Creative plan provider call failed unexpectedly") from exc

        try:
            if not result.raw_output.strip():
                raise ValueError("raw_output is empty")
            validated = response_schema.model_validate(result.data)
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            raise _invalid_output_error() from exc
        return result, validated

    @staticmethod
    def _new_plan(
        *,
        product_id: int,
        plan_type: CreativePlanType,
        title: str,
        content: dict[str, object],
        rationale: str,
        context: CreativePlanContext,
        provider_result: StructuredLLMResult,
    ) -> CreativePlan:
        return CreativePlan(
            product_id=product_id,
            plan_type=plan_type,
            title=title,
            content_json=content,
            rationale_text=rationale,
            status=CreativePlanStatus.DRAFT,
            provider_name=provider_result.provider_name,
            model_name=provider_result.model_name,
            usage_json=provider_result.usage,
            input_context_json=context.model_dump(mode="json"),
        )

    def _save_generated_batch(
        self, plans: list[CreativePlan]
    ) -> list[CreativePlan]:
        try:
            for plan in plans:
                self.plans.add(plan)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for plan in plans:
            self.db.refresh(plan)
        return plans


def _validate_content(
    plan_type: CreativePlanType, content: dict[str, object]
) -> dict[str, object]:
    schema = (
        MainImagePlanContent
        if plan_type == CreativePlanType.MAIN_IMAGE
        else VideoScriptContent
    )
    try:
        return schema.model_validate(content).model_dump(mode="json")
    except ValidationError as exc:
        raise AppError(
            status_code=422,
            code="invalid_creative_plan_content",
            message=f"content_json is invalid for {plan_type.value}",
        ) from exc


def _validate_status_transition(
    current: CreativePlanStatus, desired: CreativePlanStatus
) -> None:
    allowed = {
        CreativePlanStatus.DRAFT: {
            CreativePlanStatus.SELECTED,
            CreativePlanStatus.ARCHIVED,
        },
        CreativePlanStatus.SELECTED: {CreativePlanStatus.ARCHIVED},
        CreativePlanStatus.ARCHIVED: set(),
    }
    if desired not in allowed[current]:
        raise AppError(
            status_code=409,
            code="invalid_creative_plan_status_transition",
            message=f"Cannot change creative plan from {current.value} to {desired.value}",
        )


def _invalid_output_error() -> AppError:
    return AppError(
        status_code=502,
        code="invalid_llm_output",
        message="Creative plan provider returned invalid structured output",
    )


def _provider_error(status_code: int, code: str, message: str) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
