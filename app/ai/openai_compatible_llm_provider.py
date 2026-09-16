"""OpenAI-compatible chat provider with bounded retries and strict JSON parsing."""

import json
import time
from collections.abc import Callable
from typing import Any

import httpx2
from pydantic import BaseModel, SecretStr, ValidationError

from app.ai.llm_provider import (
    InvalidLLMOutputError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredLLMResult,
)


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        client: httpx2.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = _required_text(base_url, "LLM_BASE_URL").rstrip("/")
        self.api_key = api_key
        if not api_key.get_secret_value().strip():
            raise LLMConfigurationError("LLM_API_KEY is required")
        self.model = _required_text(model, "LLM_MODEL")
        if timeout_seconds <= 0:
            raise LLMConfigurationError("LLM_TIMEOUT_SECONDS must be greater than zero")
        if max_retries < 0:
            raise LLMConfigurationError("LLM_MAX_RETRIES cannot be negative")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client
        self.sleep = sleep

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> StructuredLLMResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n"
                        "只输出一个 JSON 对象，不要输出解释文字或额外 Markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\nOUTPUT_JSON_SCHEMA:\n"
                        f"{json.dumps(response_schema.model_json_schema(), ensure_ascii=False)}"
                    ),
                },
            ],
        }
        if self.client is not None:
            return self._request(self.client, payload, response_schema)
        with httpx2.Client(timeout=self.timeout_seconds) as client:
            return self._request(client, payload, response_schema)

    def _request(
        self,
        client: httpx2.Client,
        payload: dict[str, Any],
        response_schema: type[BaseModel],
    ) -> StructuredLLMResult:
        response: httpx2.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx2.TimeoutException as exc:
                if self._retry(attempt):
                    continue
                raise LLMTimeoutError("LLM request timed out") from exc
            except httpx2.RequestError as exc:
                if self._retry(attempt):
                    continue
                raise LLMProviderError("LLM network request failed") from exc

            if response.status_code in {401, 403}:
                raise LLMAuthenticationError("LLM authentication failed")
            if response.status_code == 429:
                if self._retry(attempt):
                    continue
                raise LLMRateLimitError("LLM rate limit retries exhausted")
            if 500 <= response.status_code <= 599:
                if self._retry(attempt):
                    continue
                raise LLMProviderError("LLM server error retries exhausted")
            if response.status_code >= 400:
                raise LLMProviderError(
                    f"LLM request was rejected with HTTP {response.status_code}"
                )
            return _parse_success_response(response, response_schema, self.model)

        raise LLMProviderError("LLM request failed without a response")

    def _retry(self, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        self.sleep(float(2**attempt))
        return True


def _parse_success_response(
    response: httpx2.Response,
    response_schema: type[BaseModel],
    model: str,
) -> StructuredLLMResult:
    try:
        response_payload = response.json()
        raw_output = response_payload["choices"][0]["message"]["content"]
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise TypeError("message content is empty")
        parsed = json.loads(_strip_json_fence(raw_output))
        validated = response_schema.model_validate(parsed)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
        raise InvalidLLMOutputError("LLM returned invalid structured output") from exc

    usage_payload = response_payload.get("usage")
    usage = None
    if isinstance(usage_payload, dict):
        supported = ("prompt_tokens", "completion_tokens", "total_tokens")
        normalized = {
            key: value
            for key in supported
            if isinstance((value := usage_payload.get(key)), int) and value >= 0
        }
        usage = normalized or None

    response_model = response_payload.get("model")
    return StructuredLLMResult(
        data=validated.model_dump(),
        raw_output=raw_output,
        source_type="ai",
        provider_name="openai_compatible",
        model_name=response_model if isinstance(response_model, str) else model,
        usage=usage,
    )


def _strip_json_fence(raw_output: str) -> str:
    content = raw_output.strip()
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        return content
    opening = lines[0].strip().lower()
    if opening not in {"```", "```json"}:
        return content
    return "\n".join(lines[1:-1]).strip()


def _required_text(value: str, setting_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMConfigurationError(f"{setting_name} is required")
    return value.strip()
