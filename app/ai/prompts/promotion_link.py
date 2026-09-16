"""Prompt structure for a promotion-link parameter suggestion."""

import json

from app.schemas.promotion_link import PromotionLinkSuggestionContext


PROMOTION_LINK_SYSTEM_PROMPT = """你是电商运营分析助手。
请只根据提供的商品、已选择创意方案和已审核素材信息，生成一条结构化推广链接参数建议。
不得编造销量、转化率、平台数据或用户反馈；信息不足时使用保守、可解释的命名。
只建议链接名称、使用场景和 UTM 参数，不执行真实投放、不创建平台广告、不修改预算。
不得生成 tracking_code；不得猜测或生成 target_url，这两项由后端和用户分别控制。
输出必须严格符合给定 Schema，不要输出 Markdown。"""


def build_promotion_link_user_prompt(
    context: PromotionLinkSuggestionContext,
) -> str:
    payload = json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
    return (
        "根据以下白名单业务数据生成推广链接参数建议。"
        "不要输出 tracking_code 或 target_url。\n"
        f"PROMOTION_LINK_INPUT_JSON:\n{payload}"
    )
