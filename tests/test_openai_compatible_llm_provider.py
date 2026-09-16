"""Configuration, HTTP, retry and end-to-end tests without real network access."""

import json
from collections.abc import Callable
from decimal import Decimal

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import build_llm_provider, get_llm_provider
from app.ai.llm_provider import (
    InvalidLLMOutputError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.mock_llm_provider import MockLLMProvider
from app.ai.openai_compatible_llm_provider import OpenAICompatibleLLMProvider
from app.core.config import Settings
from app.main import app
from app.models.product import Product, ProductStatus
from app.models.product_diagnosis import ProductDiagnosis
from app.models.store import Platform, Store
from app.models.user import UserRole


class TinyOutput(BaseModel):
    message: str
    items: list[str]


VALID_DIAGNOSIS = {
    "positioning": "真实 Provider Fake 响应定位",
    "price_band": "中等价格带",
    "audience_insights": ["通勤用户"],
    "pain_points": ["收纳不便"],
    "selling_point_analysis": ["轻量特征明确"],
    "risks": ["数据样本有限"],
    "recommendations": ["补充真实反馈"],
}


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite+pysqlite:///:memory:",
        "jwt_secret_key": "test-only-secret-key-with-at-least-32-characters",
        "llm_provider": "openai_compatible",
        "llm_base_url": "https://llm.example.test/v1",
        "llm_api_key": "unit-test-placeholder-key",
        "llm_model": "test-model",
        "llm_timeout_seconds": 5,
        "llm_max_retries": 2,
    }
    values.update(overrides)
    return Settings(**values)


def success_response(
    content: str,
    *,
    model: str = "response-model",
    usage: dict[str, int] | None = None,
) -> httpx2.Response:
    body: dict[str, object] = {
        "model": model,
        "choices": [{"message": {"content": content}}],
    }
    if usage is not None:
        body["usage"] = usage
    return httpx2.Response(200, json=body)


def make_provider(
    handler: Callable[[httpx2.Request], httpx2.Response],
    *,
    max_retries: int = 2,
    sleeps: list[float] | None = None,
) -> OpenAICompatibleLLMProvider:
    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    sleep_calls = sleeps if sleeps is not None else []
    return OpenAICompatibleLLMProvider(
        base_url="https://llm.example.test/v1",
        api_key=make_settings().llm_api_key,
        model="test-model",
        timeout_seconds=5,
        max_retries=max_retries,
        client=client,
        sleep=sleep_calls.append,
    )


def call_provider(provider: OpenAICompatibleLLMProvider):
    return provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_schema=TinyOutput,
    )


def test_factory_selects_mock_provider() -> None:
    provider = build_llm_provider(make_settings(llm_provider="mock"))
    assert isinstance(provider, MockLLMProvider)


def test_factory_selects_real_provider() -> None:
    provider = build_llm_provider(make_settings())
    assert isinstance(provider, OpenAICompatibleLLMProvider)


@pytest.mark.parametrize(
    ("overrides", "expected_setting"),
    [
        ({"llm_base_url": None}, "LLM_BASE_URL"),
        ({"llm_api_key": None}, "LLM_API_KEY"),
        ({"llm_model": None}, "LLM_MODEL"),
    ],
)
def test_real_provider_rejects_missing_required_configuration(
    overrides: dict[str, object], expected_setting: str
) -> None:
    with pytest.raises(LLMConfigurationError, match=expected_setting):
        build_llm_provider(make_settings(**overrides))


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(LLMConfigurationError, match="LLM_PROVIDER"):
        build_llm_provider(make_settings(llm_provider="automatic"))


def test_200_json_is_validated_and_metadata_is_returned() -> None:
    captured: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return success_response(
            '{"message":"ok","items":["one"]}',
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    result = call_provider(make_provider(handler))

    assert result.data == {"message": "ok", "items": ["one"]}
    assert result.source_type == "ai"
    assert result.provider_name == "openai_compatible"
    assert result.model_name == "response-model"
    assert result.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
    assert len(captured) == 1
    assert captured[0].url.path == "/v1/chat/completions"
    assert captured[0].headers["authorization"] == "Bearer unit-test-placeholder-key"
    sent = json.loads(captured[0].content)
    assert sent["model"] == "test-model"
    assert "OUTPUT_JSON_SCHEMA" in sent["messages"][1]["content"]


def test_200_fenced_json_is_accepted() -> None:
    provider = make_provider(
        lambda _: success_response('```json\n{"message":"ok","items":[]}\n```')
    )
    assert call_provider(provider).data["message"] == "ok"


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '{"message":"missing items"}',
        '```python\n{"message":"ok","items":[]}\n```',
    ],
)
def test_invalid_json_or_schema_is_not_retried(content: str) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return success_response(content)

    with pytest.raises(InvalidLLMOutputError):
        call_provider(make_provider(handler))
    assert calls == 1


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_errors_are_not_retried(status_code: int) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(status_code, json={"error": "auth"})

    with pytest.raises(LLMAuthenticationError):
        call_provider(make_provider(handler))
    assert calls == 1


def test_400_is_not_retried() -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(400, json={"error": "bad request"})

    with pytest.raises(LLMProviderError, match="HTTP 400"):
        call_provider(make_provider(handler))
    assert calls == 1


@pytest.mark.parametrize("retry_status", [429, 500])
def test_retryable_http_status_retries_then_succeeds(retry_status: int) -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(retry_status, json={"error": "temporary"})
        return success_response('{"message":"ok","items":[]}')

    result = call_provider(make_provider(handler, sleeps=sleeps))
    assert result.data["message"] == "ok"
    assert calls == 2
    assert sleeps == [1.0]


def test_timeout_retries_then_succeeds_without_real_sleep() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx2.ReadTimeout("temporary timeout", request=request)
        return success_response('{"message":"ok","items":[]}')

    result = call_provider(make_provider(handler, sleeps=sleeps))
    assert result.data["message"] == "ok"
    assert calls == 2
    assert sleeps == [1.0]


def test_network_error_stops_at_max_retries() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise httpx2.ConnectError("offline", request=request)

    with pytest.raises(LLMProviderError, match="network"):
        call_provider(make_provider(handler, max_retries=2, sleeps=sleeps))
    assert calls == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [(429, LLMRateLimitError), (500, LLMProviderError)],
)
def test_retryable_status_stops_at_max_retries(
    status_code: int, expected_error: type[LLMProviderError]
) -> None:
    calls = 0

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(status_code, json={"error": "temporary"})

    with pytest.raises(expected_error):
        call_provider(make_provider(handler, max_retries=1))
    assert calls == 2


def test_timeout_stops_at_max_retries() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise httpx2.ReadTimeout("timeout", request=request)

    with pytest.raises(LLMTimeoutError):
        call_provider(make_provider(handler, max_retries=1))
    assert calls == 2


def add_product(db: Session) -> Product:
    store = Store(store_name="真实 Provider 测试店铺", platform=Platform.OTHER)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name="真实 Provider 测试商品",
        platform=Platform.OTHER,
        price=Decimal("88.00"),
        selling_points=["测试卖点"],
        images_json=[],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_fake_http_real_provider_runs_full_diagnosis_flow(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    provider = make_provider(
        lambda _: success_response(
            json.dumps(VALID_DIAGNOSIS, ensure_ascii=False),
            model="fake-real-model",
            usage={"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
        )
    )
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(
        f"/api/v1/products/{product.id}/diagnoses/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 201
    body = response.json()
    assert body["positioning"] == VALID_DIAGNOSIS["positioning"]
    assert body["source_type"] == "ai"
    assert body["provider_name"] == "openai_compatible"
    assert body["model_name"] == "fake-real-model"
    assert body["usage_json"]["total_tokens"] == 50
    saved = db_session.get(ProductDiagnosis, body["id"])
    assert saved.raw_output == json.dumps(VALID_DIAGNOSIS, ensure_ascii=False)


def test_fake_http_provider_failure_does_not_save_diagnosis(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    provider = make_provider(
        lambda _: httpx2.Response(401, json={"error": "invalid key"})
    )
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(
        f"/api/v1/products/{product.id}/diagnoses/generate",
        headers=auth_headers_factory(UserRole.ADMIN),
    )
    app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_authentication_error"
    assert db_session.scalar(select(func.count()).select_from(ProductDiagnosis)) == 0
