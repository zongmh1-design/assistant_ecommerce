"""Prompt for an advisory-only, human-controlled advertising experiment plan."""

import json

from app.schemas.ad_experiment import AdExperimentContext


AD_EXPERIMENT_SYSTEM_PROMPT = """你是电商投放实验规划助手。
根据已由人工确认的投放建议，生成一条可执行但仍需人工控制的结构化实验计划。
不得执行广告投放、调用广告平台、修改真实预算、自动出价或扣费。
不得编造历史 CTR、CVR、ROI、曝光或转化，不得承诺收益；成功指标只能定义后续如何观察。
必须把 hypothesis_text 写成待验证假设，而不是事实结论。
只使用 Context 提供的素材和链接业务别名，不能猜测数据库 ID、tracking_code 或 target_url。
没有绑定素材或链接时应明确数据不足，但仍可生成计划。
输出必须严格符合给定 Schema，不要输出 Markdown。"""


def build_ad_experiment_user_prompt(context: AdExperimentContext) -> str:
    payload = json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
    return (
        "请根据以下白名单数据生成一条 draft 实验计划。\n"
        f"AD_EXPERIMENT_INPUT_JSON:\n{payload}"
    )
