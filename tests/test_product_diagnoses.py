"""Product diagnosis context, generation, history, editing and failure tests."""

import json
from collections.abc import Callable, Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.main import app
from app.models.competitor import Competitor
from app.models.product import Product, ProductStatus
from app.models.product_diagnosis import ProductDiagnosis
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.schemas.product_diagnosis import ProductDiagnosisOutput


VALID_OUTPUT: dict[str, object] = {
    "positioning": "面向通勤用户的轻量实用商品",
    "price_band": "当前样本属于中等价格带",
    "audience_insights": ["重视实用性", "关注价格与质量平衡"],
    "pain_points": ["选择成本高", "商品差异不清晰"],
    "selling_point_analysis": ["轻量特点明确", "耐用性需要数据验证"],
    "risks": ["竞品样本有限", "缺少真实转化数据"],
    "recommendations": ["补充产品参数", "验证核心卖点"],
}


class CapturingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[object],
    ) -> StructuredLLMResult:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
            }
        )
        return StructuredLLMResult(
            data=VALID_OUTPUT,
            raw_output=json.dumps(
                {"provider": "capturing_mock", "output": VALID_OUTPUT},
                ensure_ascii=False,
            ),
            source_type="mock_ai",
        )


class FailingProvider:
    def generate_structured(self, **_: object) -> StructuredLLMResult:
        raise LLMProviderError("deterministic provider failure")


class InvalidOutputProvider:
    def generate_structured(self, **_: object) -> StructuredLLMResult:
        return StructuredLLMResult(
            data={"positioning": "字段不完整"},
            raw_output='{"positioning":"字段不完整"}',
            source_type="mock_ai",
        )


@pytest.fixture
def provider_override() -> Generator[Callable[[object], None], None, None]:
    def set_provider(provider: object) -> None:
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, *, name: str = "轻量通勤背包") -> Product:
    store = Store(store_name=f"{name}店铺", platform=Platform.TAOBAO)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=name,
        platform=Platform.TAOBAO,
        category="箱包",
        price=Decimal("129.90"),
        cost=Decimal("52.50"),
        target_audience="需要轻量通勤装备的上班族",
        selling_points=["轻量", "分区收纳"],
        images_json=[],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_competitor(
    db: Session, *, product: Product, name: str, price: Decimal
) -> Competitor:
    competitor = Competitor(
        product_id=product.id,
        name=name,
        platform=Platform.JD,
        url=f"https://example.com/{name}",
        price=price,
        title=f"{name}标题",
        sales_hint="公开页展示销量提示",
        selling_points=["耐用", "容量大"],
        review_keywords=["质量", "容量"],
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


def generate(
    client: TestClient, product_id: int, headers: dict[str, str]
) -> object:
    return client.post(
        f"/api/v1/products/{product_id}/diagnoses/generate",
        headers=headers,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_generate_structured_mock_diagnosis(
    role: UserRole,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate(client, product.id, auth_headers_factory(role))

    assert response.status_code == 201
    body = response.json()
    ProductDiagnosisOutput.model_validate(
        {field_name: body[field_name] for field_name in ProductDiagnosisOutput.model_fields}
    )
    assert response.json()["source_type"] == "mock_ai"
    assert all(response.json()[field] for field in VALID_OUTPUT)


def test_viewer_cannot_generate_diagnosis(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate(
        client, product.id, auth_headers_factory(UserRole.VIEWER)
    )

    assert response.status_code == 403


def test_missing_product_generation_returns_404(
    client: TestClient,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    response = generate(client, 9999, auth_headers_factory(UserRole.ADMIN))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


def test_generation_without_competitors_is_allowed(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate(client, product.id, auth_headers_factory(UserRole.OPERATOR))

    assert response.status_code == 201
    assert "没有竞品样本" in response.json()["price_band"]


def test_multiple_competitors_are_mapped_to_minimal_context(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
    provider_override: Callable[[object], None],
) -> None:
    product = add_product(db_session)
    add_competitor(db_session, product=product, name="竞品甲", price=Decimal("99.00"))
    add_competitor(db_session, product=product, name="竞品乙", price=Decimal("159.00"))
    provider = CapturingProvider()
    provider_override(provider)

    response = generate(client, product.id, auth_headers_factory(UserRole.ADMIN))

    assert response.status_code == 201
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["response_schema"] is ProductDiagnosisOutput
    assert "禁止编造" in str(call["system_prompt"])
    payload = str(call["user_prompt"]).split("DIAGNOSIS_INPUT_JSON:\n", 1)[1]
    context = json.loads(payload)
    assert set(context["product"]) == {
        "name", "platform", "category", "price", "cost",
        "target_audience", "selling_points",
    }
    assert len(context["competitors"]) == 2
    assert set(context["competitors"][0]) == {
        "name", "platform", "price", "title", "sales_hint",
        "selling_points", "review_keywords",
    }
    assert "id" not in payload
    assert "created_at" not in payload
    assert "updated_at" not in payload


def test_generated_diagnosis_and_mock_raw_output_are_saved(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate(client, product.id, auth_headers_factory(UserRole.ADMIN))

    saved = db_session.get(ProductDiagnosis, response.json()["id"])
    assert saved is not None
    assert saved.product_id == product.id
    assert saved.source_type == "mock_ai"
    assert saved.input_context_json["product"]["name"] == product.name
    assert "id" not in saved.input_context_json["product"]
    raw = json.loads(saved.raw_output)
    assert raw["provider"] == "mock_llm"
    assert raw["mock"] is True


def test_history_list_returns_latest_first_and_supports_pagination(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    first = generate(client, product.id, headers).json()
    second = generate(client, product.id, headers).json()

    response = client.get(
        f"/api/v1/products/{product.id}/diagnoses?page=1&page_size=1",
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["id"] == second["id"]
    assert first["id"] != second["id"]


def test_get_diagnosis_detail_and_missing_cases(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = generate(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()
    viewer = auth_headers_factory(UserRole.VIEWER)

    detail = client.get(
        f"/api/v1/products/{product.id}/diagnoses/{created['id']}",
        headers=viewer,
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]

    missing_diagnosis = client.get(
        f"/api/v1/products/{product.id}/diagnoses/9999", headers=viewer
    )
    assert missing_diagnosis.status_code == 404
    assert missing_diagnosis.json()["error"]["code"] == "product_diagnosis_not_found"

    missing_product = client.get(
        "/api/v1/products/9999/diagnoses", headers=viewer
    )
    assert missing_product.status_code == 404


def test_operator_can_edit_all_structured_fields(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = generate(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()
    edited = {
        "positioning": "人工确认后的定位",
        "price_band": "人工确认后的价格带",
        "audience_insights": ["人工人群洞察"],
        "pain_points": ["人工痛点"],
        "selling_point_analysis": ["人工卖点分析"],
        "risks": ["人工风险"],
        "recommendations": ["人工建议"],
    }

    response = client.patch(
        f"/api/v1/products/{product.id}/diagnoses/{created['id']}",
        json=edited,
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 200
    for field_name, value in edited.items():
        assert response.json()[field_name] == value
    assert response.json()["source_type"] == "mock_ai"


def test_viewer_cannot_edit_diagnosis(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = generate(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()

    response = client.patch(
        f"/api/v1/products/{product.id}/diagnoses/{created['id']}",
        json={"positioning": "viewer 不可修改"},
        headers=auth_headers_factory(UserRole.VIEWER),
    )

    assert response.status_code == 403


def test_diagnosis_cannot_be_edited_through_another_product(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product_a = add_product(db_session, name="商品A")
    product_b = add_product(db_session, name="商品B")
    created = generate(
        client, product_b.id, auth_headers_factory(UserRole.ADMIN)
    ).json()

    response = client.patch(
        f"/api/v1/products/{product_a.id}/diagnoses/{created['id']}",
        json={"positioning": "禁止跨商品修改"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 404
    db_session.refresh(db_session.get(ProductDiagnosis, created["id"]))
    assert db_session.get(ProductDiagnosis, created["id"]).positioning != "禁止跨商品修改"


@pytest.mark.parametrize("field_name", ["id", "product_id", "source_type"])
def test_edit_rejects_protected_fields(
    field_name: str,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = generate(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()

    response = client.patch(
        f"/api/v1/products/{product.id}/diagnoses/{created['id']}",
        json={field_name: 999 if field_name != "source_type" else "ai"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("provider", "expected_code"),
    [
        (FailingProvider(), "llm_provider_error"),
        (InvalidOutputProvider(), "invalid_llm_output"),
    ],
)
def test_provider_failure_or_invalid_output_does_not_save_diagnosis(
    provider: object,
    expected_code: str,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
    provider_override: Callable[[object], None],
) -> None:
    product = add_product(db_session)
    provider_override(provider)

    response = generate(client, product.id, auth_headers_factory(UserRole.ADMIN))

    assert response.status_code == 502
    assert response.json()["error"]["code"] == expected_code
    assert db_session.scalar(select(func.count()).select_from(ProductDiagnosis)) == 0
