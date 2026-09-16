"""Manual smoke test for an explicitly configured real LLM provider."""

from pydantic import BaseModel, ValidationError

from app.ai.dependencies import build_llm_provider
from app.ai.llm_provider import LLMConfigurationError, LLMProviderError
from app.core.config import get_settings


class ProviderSmokeOutput(BaseModel):
    message: str


def main() -> int:
    print("REAL NETWORK VALIDATION")
    try:
        settings = get_settings()
    except ValidationError:
        print(
            "Configuration is incomplete. Set the required application and "
            "LLM values in the local .env file."
        )
        return 1
    if settings.llm_provider.strip().lower() != "openai_compatible":
        print(
            "LLM_PROVIDER must be openai_compatible; "
            "no real network request was made."
        )
        return 1
    if settings.llm_api_key is None or not (
        settings.llm_api_key.get_secret_value().strip()
    ):
        print("LLM_API_KEY is missing; no real network request was made.")
        return 1
    try:
        provider = build_llm_provider(settings)
        result = provider.generate_structured(
            system_prompt="You are a connectivity test. Return only valid JSON.",
            user_prompt='Return exactly one object with a short message such as {"message":"ok"}.',
            response_schema=ProviderSmokeOutput,
        )
        ProviderSmokeOutput.model_validate(result.data)
    except (LLMConfigurationError, LLMProviderError) as exc:
        print(f"LLM provider verification failed: {type(exc).__name__}")
        return 1
    output = ProviderSmokeOutput.model_validate(result.data)
    output_format = (
        "markdown_json_fence"
        if result.raw_output.strip().startswith("```")
        else "plain_json"
    )
    print(
        "request=success\n"
        f"provider={result.provider_name}\n"
        f"model={result.model_name}\n"
        f"structured_message={output.message}\n"
        f"output_format={output_format}\n"
        f"usage_present={result.usage is not None}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
