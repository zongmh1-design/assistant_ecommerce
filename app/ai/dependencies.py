"""Central composition point for the configured LLM provider."""

import httpx2
from collections.abc import Callable

from app.ai.llm_provider import LLMConfigurationError, LLMProvider
from app.ai.mock_llm_provider import MockLLMProvider
from app.ai.openai_compatible_llm_provider import OpenAICompatibleLLMProvider
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError


def get_llm_provider() -> LLMProvider:
    try:
        return build_llm_provider(get_settings())
    except LLMConfigurationError as exc:
        raise AppError(
            status_code=503,
            code="llm_configuration_error",
            message="LLM provider is not configured",
        ) from exc


def build_llm_provider(
    settings: Settings,
    *,
    client: httpx2.Client | None = None,
    sleep: Callable[[float], None] | None = None,
) -> LLMProvider:
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name != "openai_compatible":
        raise LLMConfigurationError(
            "LLM_PROVIDER must be 'mock' or 'openai_compatible'"
        )
    if not settings.llm_base_url or not settings.llm_base_url.strip():
        raise LLMConfigurationError("LLM_BASE_URL is required")
    if settings.llm_api_key is None or not settings.llm_api_key.get_secret_value().strip():
        raise LLMConfigurationError("LLM_API_KEY is required")
    if not settings.llm_model or not settings.llm_model.strip():
        raise LLMConfigurationError("LLM_MODEL is required")

    if sleep is None:
        return OpenAICompatibleLLMProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            client=client,
        )
    return OpenAICompatibleLLMProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        client=client,
        sleep=sleep,
    )
