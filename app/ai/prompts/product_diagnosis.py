"""Provider-neutral prompt construction for structured product diagnosis."""

import json

from app.schemas.product_diagnosis import ProductDiagnosisContext


PRODUCT_DIAGNOSIS_SYSTEM_PROMPT = """你是电商运营分析助手。
根据用户提供的商品信息和竞品信息，生成结构化商品诊断。
只能使用输入中明确提供的数据，禁止编造销量、评价、市场份额或平台数据。
数据缺失时必须在相应分析字段中明确说明信息不足。
输出必须严格符合调用方指定的 Pydantic Schema。
你只提供分析和建议，不执行广告投放、价格修改或任何外部平台操作。"""


def build_product_diagnosis_user_prompt(context: ProductDiagnosisContext) -> str:
    context_json = json.dumps(
        context.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    competitor_note = (
        "当前提供了竞品信息，请进行有依据的对比。"
        if context.competitors
        else "当前没有竞品信息，请明确竞品对比依据不足，不要虚构竞品。"
    )
    return f"""请基于以下业务上下文生成商品诊断。
{competitor_note}

DIAGNOSIS_INPUT_JSON:
{context_json}
"""
