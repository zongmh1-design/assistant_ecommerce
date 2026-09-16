"""Prompt construction for three structured main-image directions."""

import json

from app.schemas.creative_plan import CreativePlanContext


MAIN_IMAGE_PLAN_SYSTEM_PROMPT = """你是电商主图创意策划助手。
只根据给定商品和可选诊断信息，输出三个结构化主图创意方向。
禁止编造销量、市场份额、用户评价或未提供的商品能力。
缺少诊断时只使用已知商品信息，并明确保持保守判断。
输出必须符合指定 Schema。本任务只设计主图方案，不生成图片、不调用外部平台、不执行广告投放。"""


def build_main_image_plan_user_prompt(context: CreativePlanContext) -> str:
    return _creative_prompt("请生成三个差异明确的主图创意方向。", context)


def _creative_prompt(instruction: str, context: CreativePlanContext) -> str:
    context_json = json.dumps(
        context.model_dump(mode="json"), ensure_ascii=False, indent=2
    )
    diagnosis_note = (
        "已提供商品诊断，可引用其中有依据的结论。"
        if context.diagnosis is not None
        else "未提供商品诊断，只能根据商品已知信息生成，不得补造市场结论。"
    )
    return f"""{instruction}
{diagnosis_note}

CREATIVE_INPUT_JSON:
{context_json}
"""
