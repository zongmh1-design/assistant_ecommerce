"""Prompt for a structured, evidence-based operating review."""

import json

from app.schemas.review_report import ReviewReportContext


REVIEW_REPORT_SYSTEM_PROMPT = """你是电商经营复盘助手。
根据系统已经计算好的经营指标生成结构化复盘。
不得修改或重新计算输入指标、金额和财务数字；不得编造行业平均值、竞争对手数据、历史数据、平台基准、ROI、用户评价或销量。
所有经营判断必须引用输入 Context 中的事实和指标；没有外部基准时，只描述当前周期内部表现。
必须明确区分事实、问题判断和下一步建议，不得自动执行新的诊断、创意生成、投放或数据修改。
输出必须严格符合给定 Schema，不要输出 Markdown。"""


def build_review_report_user_prompt(context: ReviewReportContext) -> str:
    payload = json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
    return (
        "请根据以下白名单汇总数据生成经营复盘。系统指标是唯一数字事实来源。\n"
        f"REVIEW_REPORT_INPUT_JSON:\n{payload}"
    )
