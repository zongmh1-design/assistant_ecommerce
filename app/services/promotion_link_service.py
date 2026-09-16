"""Promotion-link suggestions, lifecycle and transactional click recording."""

from __future__ import annotations

import secrets

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
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
from app.ai.promotion_link_context import build_promotion_link_context
from app.ai.prompts.promotion_link import (
    PROMOTION_LINK_SYSTEM_PROMPT,
    build_promotion_link_user_prompt,
)
from app.core.exceptions import AppError
from app.models.product import Product
from app.models.promotion_link import PromotionLink, PromotionLinkClick, PromotionLinkStatus
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.repositories.generated_asset_repository import GeneratedAssetRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_link_click_repository import PromotionLinkClickRepository
from app.repositories.promotion_link_repository import PromotionLinkRepository
from app.schemas.promotion_link import PromotionLinkCreate, PromotionLinkSuggestion, PromotionLinkUpdate


class PromotionLinkService:
    TRACKING_CODE_BYTES = 9
    MAX_TRACKING_CODE_ATTEMPTS = 10

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.plans = CreativePlanRepository(db)
        self.assets = GeneratedAssetRepository(db)
        self.links = PromotionLinkRepository(db)
        self.clicks = PromotionLinkClickRepository(db)

    def generate_suggestion(self, product_id: int, provider: LLMProvider) -> PromotionLinkSuggestion:
        product = self._require_product(product_id)
        context = build_promotion_link_context(
            product,
            self.plans.get_latest_selected_by_product(product_id),
            self.assets.get_latest_approved_by_product(product_id),
        )
        try:
            result = provider.generate_structured(
                system_prompt=PROMOTION_LINK_SYSTEM_PROMPT,
                user_prompt=build_promotion_link_user_prompt(context),
                response_schema=PromotionLinkSuggestion,
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
            raise _provider_error(502, "llm_provider_error", "Promotion-link suggestion provider call failed") from exc
        except Exception as exc:
            raise _provider_error(502, "llm_provider_error", "Promotion-link suggestion provider call failed unexpectedly") from exc
        return _validate_suggestion_result(result)

    def create(self, product_id: int, payload: PromotionLinkCreate) -> PromotionLink:
        self._require_product(product_id)
        values = payload.model_dump()
        values["target_url"] = str(payload.target_url)
        values["utm_json"] = payload.utm_json.model_dump(exclude_none=True)
        for _ in range(self.MAX_TRACKING_CODE_ATTEMPTS):
            tracking_code = secrets.token_urlsafe(self.TRACKING_CODE_BYTES)
            if self.links.tracking_code_exists(tracking_code):
                continue
            link = PromotionLink(
                product_id=product_id,
                tracking_code=tracking_code,
                status=PromotionLinkStatus.ACTIVE,
                click_count=0,
                **values,
            )
            self.links.add(link)
            try:
                self.db.commit()
                self.db.refresh(link)
                return link
            except IntegrityError:
                # 数据库唯一约束是并发碰撞的最终兜底；回滚后生成新码重试。
                self.db.rollback()
            except Exception:
                self.db.rollback()
                raise
        raise AppError(
            status_code=503,
            code="tracking_code_generation_failed",
            message="A unique tracking code could not be allocated",
        )

    def list(self, *, product_id: int, status: PromotionLinkStatus | None, page: int, page_size: int) -> tuple[list[PromotionLink], int]:
        self._require_product(product_id)
        return self.links.list_by_product(
            product_id=product_id, status=status, offset=(page - 1) * page_size, limit=page_size
        )

    def get(self, product_id: int, link_id: int) -> PromotionLink:
        self._require_product(product_id)
        link = self.links.get_by_id_and_product_id(link_id, product_id)
        if link is None:
            raise _link_not_found(link_id)
        return link

    def update(self, product_id: int, link_id: int, payload: PromotionLinkUpdate) -> PromotionLink:
        link = self.get(product_id, link_id)
        changes = payload.model_dump(exclude_unset=True)
        if "target_url" in changes:
            changes["target_url"] = str(payload.target_url)
        if "utm_json" in changes:
            changes["utm_json"] = payload.utm_json.model_dump(exclude_none=True)
        for field_name, value in changes.items():
            setattr(link, field_name, value)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(link)
        return link

    def record_click(self, tracking_code: str, *, client_ip: str | None, user_agent: str | None) -> str:
        link = self.links.get_by_tracking_code(tracking_code)
        if link is None:
            raise AppError(
                status_code=404,
                code="promotion_link_not_found",
                message="Promotion link was not found",
            )
        if link.status != PromotionLinkStatus.ACTIVE:
            raise _inactive_link()
        target_url = link.target_url
        try:
            self.clicks.add(PromotionLinkClick(
                promotion_link_id=link.id, client_ip=client_ip, user_agent=user_agent
            ))
            self.db.flush()
            if not self.links.increment_click_count_atomic(link.id):
                raise _inactive_link()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return target_url

    def list_clicks(self, *, product_id: int, link_id: int, page: int, page_size: int) -> tuple[list[PromotionLinkClick], int]:
        self.get(product_id, link_id)
        return self.clicks.list_by_link(
            link_id=link_id, offset=(page - 1) * page_size, limit=page_size
        )

    def _require_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )
        return product


def _validate_suggestion_result(result: StructuredLLMResult) -> PromotionLinkSuggestion:
    try:
        if not result.raw_output.strip():
            raise ValueError("raw_output is empty")
        return PromotionLinkSuggestion.model_validate(result.data)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise AppError(
            status_code=502,
            code="invalid_llm_output",
            message="Promotion-link provider returned invalid structured output",
        ) from exc


def _link_not_found(link_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="promotion_link_not_found",
        message=f"Promotion link {link_id} was not found",
    )


def _inactive_link() -> AppError:
    return AppError(
        status_code=410,
        code="promotion_link_inactive",
        message="Promotion link is inactive",
    )


def _provider_error(status_code: int, code: str, message: str) -> AppError:
    return AppError(status_code=status_code, code=code, message=message)
