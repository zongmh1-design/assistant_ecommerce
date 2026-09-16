"""Manual smoke test for an explicitly configured real LLM provider."""

from pydantic import BaseModel

from app.ai.dependencies import build_llm_provider
from app.ai.llm_provider import LLMProviderError
from app.core.config import get_settings


class ProviderSmokeOutput(BaseModel):
    message: str


def main() -> int:
    settings = get_settings()
    if settings.llm_provider.strip().lower() != "openai_compatible":
        print("LLM_PROVIDER is not openai_compatible; no real network test was run.")
        return 1
    try:
        provider = build_llm_provider(settings)
        result = provider.generate_structured(
            system_prompt="You are a connectivity test. Return only valid JSON.",
            user_prompt='Return exactly one object with a short message such as {"message":"ok"}.',
            response_schema=ProviderSmokeOutput,
        )
        ProviderSmokeOutput.model_validate(result.data)
    except LLMProviderError as exc:
        print(f"LLM provider verification failed: {type(exc).__name__}")
        return 1
    print(
        "LLM provider verification succeeded: "
        f"provider={result.provider_name}, model={result.model_name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
