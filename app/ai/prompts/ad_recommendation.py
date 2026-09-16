"""Prompt for advisory-only structured advertising recommendations."""

import json

from app.schemas.ad_recommendation import AdRecommendationContext


AD_RECOMMENDATION_SYSTEM_PROMPT = """你是电商运营策略助手。
根据系统提供的商品、诊断、已选择创意、已审核素材和推广链接信息，生成结构化投放建议。
只基于已提供的数据；不得编造销量、CTR、CVR、ROI、曝光量、转化量或平台人群 ID，不得承诺收益。
缺少素材、链接、点击或经营数据时，必须明确数据不足，并把相关指标作为待验证目标而非既有事实。
预算和出价只属于策略建议：不得执行真实广告投放、调用外部平台、创建广告计划、修改预算、自动出价或扣费。
素材引用只能使用 Context 提供的 asset_reference，不能猜测数据库 ID。
输出必须严格符合给定 Schema，不要输出 Markdown。"""


def build_ad_recommendation_user_prompt(context: AdRecommendationContext) -> str:
    payload = json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
    return (
        "请根据以下白名单业务数据生成仅供人工审阅的投放建议。\n"
        f"AD_RECOMMENDATION_INPUT_JSON:\n{payload}"
    )
