"""Creative-plan generation, context, editing, queries and status rules."""

import json
from collections.abc import Callable, Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.dependencies import get_llm_provider
from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.ai.mock_llm_provider import MockLLMProvider
from app.main import app
from app.models.creative_plan import CreativePlan
from app.models.product import Product, ProductStatus
from app.models.product_diagnosis import ProductDiagnosis
from app.models.store import Platform, Store
from app.models.user import UserRole
from app.repositories.creative_plan_repository import CreativePlanRepository
from app.schemas.creative_plan import MainImagePlansOutput, VideoScriptsOutput
from app.services.creative_plan_service import CreativePlanService


def main_item(index: int) -> dict[str, object]:
    return {
        "title": f"主图方向{index}",
        "visual_structure": ["商品居中", f"方向{index}信息层级"],
        "core_copy": [f"核心文案{index}"],
        "highlighted_selling_points": ["轻量", "耐用"],
        "rationale": f"主图理由{index}",
    }


def video_item(index: int) -> dict[str, object]:
    return {
        "title": f"视频脚本{index}",
        "opening_hook": f"开头钩子{index}",
        "storyboard": [
            {
                "scene_no": 1,
                "visual": "展示使用场景",
                "duration_hint": "3秒",
                "voiceover": "场景口播",
            },
            {
                "scene_no": 2,
                "visual": "展示商品卖点",
                "duration_hint": "5秒",
                "voiceover": "卖点口播",
            },
        ],
        "voiceover": ["完整口播第一句", "完整口播第二句"],
        "conversion_cta": "查看商品详情",
        "rationale": f"视频理由{index}",
    }


VALID_MAIN_OUTPUT = {"plans": [main_item(index) for index in range(1, 4)]}
VALID_VIDEO_OUTPUT = {"scripts": [video_item(index) for index in range(1, 4)]}


class CapturingProvider:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, **kwargs: object) -> StructuredLLMResult:
        self.calls.append(kwargs)
        return StructuredLLMResult(
            data=self.output,
            raw_output=json.dumps(self.output, ensure_ascii=False),
            source_type="mock_ai",
            provider_name="capturing_fake",
            model_name="capturing-model",
            usage={"total_tokens": 30},
        )


class FailingProvider:
    def generate_structured(self, **_: object) -> StructuredLLMResult:
        raise LLMProviderError("deterministic creative failure")


@pytest.fixture
def provider_override() -> Generator[Callable[[object], None], None, None]:
    def set_provider(provider: object) -> None:
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield set_provider
    app.dependency_overrides.pop(get_llm_provider, None)


def add_product(db: Session, *, name: str = "创意方案商品") -> Product:
    store = Store(store_name=f"{name}店铺", platform=Platform.TAOBAO)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name=name,
        platform=Platform.TAOBAO,
        category="家居",
        price=Decimal("89.90"),
        target_audience="重视简洁体验的家庭用户",
        selling_points=["轻量", "耐用", "易清洁"],
        images_json=[],
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_diagnosis(
    db: Session, *, product: Product, positioning: str
) -> ProductDiagnosis:
    diagnosis = ProductDiagnosis(
        product_id=product.id,
        source_type="mock_ai",
        positioning=positioning,
        price_band="中端价格带",
        audience_insights=["家庭用户"],
        pain_points=["清洁不便"],
        selling_point_analysis=["轻量卖点明确"],
        risks=["缺少真实反馈"],
        recommendations=["验证卖点"],
        input_context_json={"product": {"name": product.name}, "competitors": []},
        raw_output="{}",
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def generate_main(
    client: TestClient, product_id: int, headers: dict[str, str]
):
    return client.post(
        f"/api/v1/products/{product_id}/creative-plans/main-images/generate",
        headers=headers,
    )


def generate_video(
    client: TestClient, product_id: int, headers: dict[str, str]
):
    return client.post(
        f"/api/v1/products/{product_id}/creative-plans/video-scripts/generate",
        headers=headers,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.OPERATOR])
def test_admin_and_operator_generate_three_main_image_drafts(
    role: UserRole,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate_main(client, product.id, auth_headers_factory(role))

    assert response.status_code == 201
    assert len(response.json()) == 3
    assert {item["plan_type"] for item in response.json()} == {"main_image"}
    assert {item["status"] for item in response.json()} == {"draft"}
    assert all(item["provider_name"] == "mock" for item in response.json())
    assert db_session.scalar(select(func.count()).select_from(CreativePlan)) == 3


def test_viewer_cannot_generate_and_missing_product_returns_404(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    assert generate_main(
        client, product.id, auth_headers_factory(UserRole.VIEWER)
    ).status_code == 403
    missing = generate_main(client, 9999, auth_headers_factory(UserRole.ADMIN))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "product_not_found"


def test_latest_diagnosis_is_mapped_to_minimal_creative_context(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
    provider_override: Callable[[object], None],
) -> None:
    product = add_product(db_session)
    add_diagnosis(db_session, product=product, positioning="旧定位")
    latest = add_diagnosis(db_session, product=product, positioning="最新定位")
    provider = CapturingProvider(VALID_MAIN_OUTPUT)
    provider_override(provider)

    response = generate_main(client, product.id, auth_headers_factory(UserRole.ADMIN))

    assert response.status_code == 201
    call = provider.calls[0]
    assert call["response_schema"] is MainImagePlansOutput
    prompt = str(call["user_prompt"])
    context = json.loads(prompt.split("CREATIVE_INPUT_JSON:\n", 1)[1])
    assert set(context["product"]) == {
        "name", "platform", "category", "price", "target_audience", "selling_points"
    }
    assert set(context["diagnosis"]) == {
        "positioning", "price_band", "audience_insights", "pain_points",
        "selling_point_analysis", "risks", "recommendations",
    }
    assert context["diagnosis"]["positioning"] == latest.positioning
    assert "raw_output" not in prompt
    assert "provider_name" not in prompt
    assert "created_at" not in prompt
    assert all(item["input_context_json"] == context for item in response.json())
    assert all(item["usage_json"] == {"total_tokens": 30} for item in response.json())


def test_generation_without_diagnosis_is_allowed_and_traced(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)

    response = generate_main(
        client, product.id, auth_headers_factory(UserRole.OPERATOR)
    )

    assert response.status_code == 201
    assert all(item["input_context_json"]["diagnosis"] is None for item in response.json())


@pytest.mark.parametrize(
    "provider",
    [
        CapturingProvider({"plans": [main_item(1)]}),
        CapturingProvider({"plans": [{"title": "字段不足"}] * 3}),
        FailingProvider(),
    ],
)
def test_invalid_main_output_or_provider_failure_saves_nothing(
    provider: object,
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
    provider_override: Callable[[object], None],
) -> None:
    product = add_product(db_session)
    provider_override(provider)

    response = generate_main(client, product.id, auth_headers_factory(UserRole.ADMIN))

    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(CreativePlan)) == 0


def test_generated_batch_rolls_back_when_second_insert_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = add_product(db_session)
    calls = 0
    original_add = CreativePlanRepository.add

    def fail_second(
        repository: CreativePlanRepository, plan: CreativePlan
    ) -> CreativePlan:
        nonlocal calls
        calls += 1
        original_add(repository, plan)
        if calls == 2:
            raise RuntimeError("simulated batch insert failure")
        return plan

    monkeypatch.setattr(CreativePlanRepository, "add", fail_second)
    with pytest.raises(RuntimeError, match="simulated batch insert failure"):
        CreativePlanService(db_session).generate_main_images(
            product.id, MockLLMProvider()
        )

    assert db_session.scalar(select(func.count()).select_from(CreativePlan)) == 0


def test_video_generation_creates_three_structured_deterministic_scripts(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)

    first = generate_video(client, product.id, headers)
    second = generate_video(client, product.id, headers)

    assert first.status_code == 201
    assert len(first.json()) == 3
    assert {item["plan_type"] for item in first.json()} == {"video_script"}
    assert all(len(item["content_json"]["storyboard"]) == 3 for item in first.json())
    first_content = [(item["title"], item["content_json"]) for item in first.json()]
    second_content = [(item["title"], item["content_json"]) for item in second.json()]
    assert first_content == second_content


def test_invalid_video_output_or_failure_saves_nothing(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
    provider_override: Callable[[object], None],
) -> None:
    product = add_product(db_session)
    provider_override(CapturingProvider({"scripts": [video_item(1)]}))

    response = generate_video(client, product.id, auth_headers_factory(UserRole.OPERATOR))

    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(CreativePlan)) == 0


def test_list_filters_latest_order_pagination_and_detail(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    writer = auth_headers_factory(UserRole.ADMIN)
    main = generate_main(client, product.id, writer).json()
    video = generate_video(client, product.id, writer).json()
    selected = client.patch(
        f"/api/v1/products/{product.id}/creative-plans/{main[0]['id']}",
        json={"status": "selected"}, headers=writer,
    ).json()
    viewer = auth_headers_factory(UserRole.VIEWER)

    by_type = client.get(
        f"/api/v1/products/{product.id}/creative-plans?plan_type=video_script",
        headers=viewer,
    )
    assert by_type.status_code == 200
    assert by_type.json()["total"] == 3
    assert by_type.json()["items"][0]["id"] == video[-1]["id"]

    by_status = client.get(
        f"/api/v1/products/{product.id}/creative-plans?status=selected&page=1&page_size=1",
        headers=viewer,
    )
    assert by_status.json()["total"] == 1
    assert by_status.json()["items"][0]["id"] == selected["id"]

    detail = client.get(
        f"/api/v1/products/{product.id}/creative-plans/{main[1]['id']}",
        headers=viewer,
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == main[1]["id"]


def test_missing_plan_and_product_return_404(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    viewer = auth_headers_factory(UserRole.VIEWER)
    missing_plan = client.get(
        f"/api/v1/products/{product.id}/creative-plans/9999", headers=viewer
    )
    assert missing_plan.status_code == 404
    assert missing_plan.json()["error"]["code"] == "creative_plan_not_found"
    assert client.get(
        "/api/v1/products/9999/creative-plans", headers=viewer
    ).status_code == 404


def test_operator_edits_content_but_viewer_and_cross_product_are_rejected(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product_a = add_product(db_session, name="商品A")
    product_b = add_product(db_session, name="商品B")
    created = generate_main(
        client, product_b.id, auth_headers_factory(UserRole.ADMIN)
    ).json()[0]
    content = {
        "visual_structure": ["人工布局"],
        "core_copy": ["人工文案"],
        "highlighted_selling_points": ["人工卖点"],
    }
    edited = client.patch(
        f"/api/v1/products/{product_b.id}/creative-plans/{created['id']}",
        json={"title": "人工标题", "content_json": content, "rationale_text": "人工理由"},
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert edited.status_code == 200
    assert edited.json()["content_json"] == content

    assert client.patch(
        f"/api/v1/products/{product_b.id}/creative-plans/{created['id']}",
        json={"title": "viewer 修改"},
        headers=auth_headers_factory(UserRole.VIEWER),
    ).status_code == 403
    assert client.patch(
        f"/api/v1/products/{product_a.id}/creative-plans/{created['id']}",
        json={"title": "跨商品修改"},
        headers=auth_headers_factory(UserRole.ADMIN),
    ).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"plan_type": "video_script"},
        {"product_id": 999},
        {"content_json": {"opening_hook": "错误类型内容"}},
    ],
)
def test_patch_rejects_protected_fields_and_invalid_content(
    payload: dict[str, object],
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    created = generate_main(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()[0]
    response = client.patch(
        f"/api/v1/products/{product.id}/creative-plans/{created['id']}",
        json=payload,
        headers=auth_headers_factory(UserRole.OPERATOR),
    )
    assert response.status_code == 422


def test_status_transitions_and_archived_is_terminal(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.OPERATOR)
    plan = generate_main(client, product.id, headers).json()[0]
    url = f"/api/v1/products/{product.id}/creative-plans/{plan['id']}"

    assert client.patch(url, json={"status": "selected"}, headers=headers).json()["status"] == "selected"
    assert client.patch(url, json={"status": "archived"}, headers=headers).json()["status"] == "archived"
    rejected = client.patch(url, json={"status": "draft"}, headers=headers)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "invalid_creative_plan_status_transition"


def test_selecting_new_plan_archives_old_selected_with_type_isolation(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    headers = auth_headers_factory(UserRole.ADMIN)
    main = generate_main(client, product.id, headers).json()
    video = generate_video(client, product.id, headers).json()

    for plan in (main[0], video[0], main[1]):
        response = client.patch(
            f"/api/v1/products/{product.id}/creative-plans/{plan['id']}",
            json={"status": "selected"}, headers=headers,
        )
        assert response.status_code == 200

    db_session.expire_all()
    assert db_session.get(CreativePlan, main[0]["id"]).status.value == "archived"
    assert db_session.get(CreativePlan, main[1]["id"]).status.value == "selected"
    assert db_session.get(CreativePlan, video[0]["id"]).status.value == "selected"
    selected_count = db_session.scalar(
        select(func.count()).select_from(CreativePlan).where(
            CreativePlan.product_id == product.id,
            CreativePlan.status == "selected",
        )
    )
    assert selected_count == 2


def test_viewer_cannot_change_status(
    client: TestClient,
    db_session: Session,
    auth_headers_factory: Callable[[UserRole], dict[str, str]],
) -> None:
    product = add_product(db_session)
    plan = generate_main(
        client, product.id, auth_headers_factory(UserRole.ADMIN)
    ).json()[0]
    response = client.patch(
        f"/api/v1/products/{product.id}/creative-plans/{plan['id']}",
        json={"status": "selected"},
        headers=auth_headers_factory(UserRole.VIEWER),
    )
    assert response.status_code == 403
