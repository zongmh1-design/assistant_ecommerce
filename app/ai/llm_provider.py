"""Small provider-neutral contract for structured LLM generation."""

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class StructuredLLMResult:
    data: Any
    raw_output: str
    source_type: str
    provider_name: str | None = None
    model_name: str | None = None
    usage: dict[str, int] | None = None


class LLMProviderError(Exception):
    """Expected provider failure translated by the business service."""


class LLMConfigurationError(LLMProviderError):
    """Required provider configuration is absent or invalid."""


class LLMAuthenticationError(LLMProviderError):
    """The remote endpoint rejected authentication or authorization."""


class LLMRateLimitError(LLMProviderError):
    """The remote endpoint kept rejecting requests because of rate limits."""


class LLMTimeoutError(LLMProviderError):
    """The remote request exceeded the configured timeout."""


class InvalidLLMOutputError(LLMProviderError):
    """The model responded, but its content is not valid structured output."""


class LLMProvider(Protocol):
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> StructuredLLMResult: ...
