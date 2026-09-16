"""Deterministic offline provider for diagnosis and creative-plan demonstrations."""

import json
from typing import Any

from pydantic import BaseModel

from app.ai.llm_provider import LLMProviderError, StructuredLLMResult
from app.schemas.ad_recommendation import AdRecommendationOutput
from app.schemas.ad_experiment import AdExperimentOutput
from app.schemas.creative_plan import MainImagePlansOutput, VideoScriptsOutput
from app.schemas.product_diagnosis import ProductDiagnosisOutput
from app.schemas.promotion_link import PromotionLinkSuggestion
from app.schemas.review_report import ReviewReportOutput


class MockLLMProvider:
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> StructuredLLMResult:
        del system_prompt
        if response_schema is ProductDiagnosisOutput:
            output = _diagnosis_output(
                _read_context(user_prompt, "DIAGNOSIS_INPUT_JSON:\n")
            )
            model_name = "mock-product-diagnosis"
        elif response_schema is MainImagePlansOutput:
            output = _main_image_output(
                _read_context(user_prompt, "CREATIVE_INPUT_JSON:\n")
            )
            model_name = "mock-main-image-plan"
        elif response_schema is VideoScriptsOutput:
            output = _video_script_output(
                _read_context(user_prompt, "CREATIVE_INPUT_JSON:\n")
            )
            model_name = "mock-video-script"
        elif response_schema is PromotionLinkSuggestion:
            output = _promotion_link_suggestion(
                _read_context(user_prompt, "PROMOTION_LINK_INPUT_JSON:\n")
            )
            model_name = "mock-promotion-link-suggestion"
        elif response_schema is AdRecommendationOutput:
            output = _ad_recommendation_output(
                _read_context(user_prompt, "AD_RECOMMENDATION_INPUT_JSON:\n")
            )
            model_name = "mock-ad-recommendation"
        elif response_schema is AdExperimentOutput:
            output = _ad_experiment_output(
                _read_context(user_prompt, "AD_EXPERIMENT_INPUT_JSON:\n")
            )
            model_name = "mock-ad-experiment"
        elif response_schema is ReviewReportOutput:
            output = _review_report_output(
                _read_context(user_prompt, "REVIEW_REPORT_INPUT_JSON:\n")
            )
            model_name = "mock-review-report"
        else:
            raise LLMProviderError(
                f"MockLLMProvider does not support schema {response_schema.__name__}"
            )
        raw_output = json.dumps(
            {"provider": "mock_llm", "mock": True, "output": output},
            ensure_ascii=False,
            sort_keys=True,
        )
        return StructuredLLMResult(
            data=output,
            raw_output=raw_output,
            source_type="mock_ai",
            provider_name="mock",
            model_name=model_name,
        )


def _diagnosis_output(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    competitors = context["competitors"]
    product_name = product["name"]
    target_audience = product.get("target_audience") or "目标人群信息不足"
    selling_points = product.get("selling_points") or []
    competitor_summary = (
        f"当前纳入 {len(competitors)} 个竞品样本，适合进行初步相对定位。"
        if competitors
        else "当前没有竞品样本，价格带和差异化判断依据不足。"
    )
    point_summary = (
        "；".join(selling_points)
        if selling_points
        else "商品卖点资料不足，需要运营人员补充"
    )
    return {
        "positioning": f"{product_name}可围绕现有商品信息建立清晰、可验证的核心定位。",
        "price_band": f"当前商品价格为 {product['price']}；{competitor_summary}",
        "audience_insights": [
            f"现有目标人群描述：{target_audience}",
            "购买决策信息仍应通过后续真实经营数据验证。",
        ],
        "pain_points": [
            "用户需要快速理解商品与替代方案的主要差异。",
            "缺少真实评价和转化数据时，痛点判断只能作为待验证假设。",
        ],
        "selling_point_analysis": [
            f"当前已提供的卖点：{point_summary}",
            "建议将卖点改写为可以被用户感知和验证的具体利益。",
        ],
        "risks": [
            "当前诊断基于有限录入资料，不代表真实市场调研结论。",
            "竞品价格、销量提示和评论关键词可能存在缺失或过时。",
        ],
        "recommendations": [
            "补充可验证的产品参数、目标用户场景和真实反馈。",
            "围绕一个核心卖点设计后续内容，并用经营数据验证效果。",
        ],
    }


def _main_image_output(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    name = product["name"]
    selling_points = product.get("selling_points") or ["商品核心信息"]
    primary_point = selling_points[0]
    directions = [
        ("核心卖点聚焦", "商品主体居中，核心卖点置于视觉第一层级", "一眼看懂核心价值"),
        ("使用场景表达", "以目标用户使用场景为背景，商品作为前景主体", "把商品放进真实需求场景"),
        ("信息对比布局", "左右分区展示主要特点和适用场景，不使用虚构竞品数据", "关键信息清晰对比"),
    ]
    return {
        "plans": [
            {
                "title": f"{name}·{title}",
                "visual_structure": [layout, "保留清晰留白和单一视觉焦点"],
                "core_copy": [copy, f"突出：{primary_point}"],
                "highlighted_selling_points": selling_points[:3],
                "rationale": f"Mock 演示方向 {index}：提供创意方向，不代表最终图片。",
            }
            for index, (title, layout, copy) in enumerate(directions, start=1)
        ]
    }


def _video_script_output(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    name = product["name"]
    selling_points = product.get("selling_points") or ["商品已知信息"]
    primary_point = selling_points[0]
    angles = ["痛点切入", "场景展示", "卖点拆解"]
    return {
        "scripts": [
            {
                "title": f"{name}·{angle}",
                "opening_hook": f"先展示目标场景中的常见需求，再引出{name}。",
                "storyboard": [
                    {
                        "scene_no": 1,
                        "visual": "展示用户使用场景和明确问题，不引用虚构数据",
                        "duration_hint": "3秒",
                        "voiceover": "遇到这种使用需求时，先关注真正影响体验的细节。",
                    },
                    {
                        "scene_no": 2,
                        "visual": f"近景展示商品及已知卖点：{primary_point}",
                        "duration_hint": "6秒",
                        "voiceover": f"{name}当前可重点表达{primary_point}。",
                    },
                    {
                        "scene_no": 3,
                        "visual": "回到完整商品画面并展示行动提示",
                        "duration_hint": "3秒",
                        "voiceover": "查看完整商品信息，再根据实际需求选择。",
                    },
                ],
                "voiceover": [
                    "从真实使用需求切入。",
                    f"重点说明已提供卖点：{primary_point}。",
                    "引导用户查看详情，不承诺未提供的效果。",
                ],
                "conversion_cta": "查看商品详情，确认是否符合你的使用需求。",
                "rationale": f"Mock 演示脚本 {index}：提供拍摄方向，不代表已生成视频。",
            }
            for index, angle in enumerate(angles, start=1)
        ]
    }


def _promotion_link_suggestion(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    plan = context.get("selected_creative_plan")
    asset = context.get("approved_asset")
    name = product["name"]
    platform = product["platform"]
    scene = (
        asset.get("usage_scene")
        if asset and asset.get("usage_scene")
        else "社交媒体商品分享"
    )
    content = plan["plan_type"] if plan else "product"
    return {
        "link_name": f"{name}·{scene}",
        "scene_text": scene,
        "utm_source": platform,
        "utm_medium": "social",
        "utm_campaign": "product_promotion",
        "utm_content": content,
        "rationale": "Mock 建议仅提供可编辑的 UTM 参数，不创建链接、不决定目标地址。",
    }


def _ad_recommendation_output(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    assets = context.get("approved_assets") or []
    links = context.get("active_promotion_links") or []
    name = product["name"]
    asset_reference = (
        assets[0]["asset_reference"] if assets else "not_available"
    )
    evidence_note = (
        f"当前有 {len(assets)} 个已审核素材和 {len(links)} 条活跃推广链接可供规划。"
        if assets or links
        else "当前没有已审核素材、推广链接或真实投放指标，所有效果均需后续实验验证。"
    )
    return {
        "summary": f"围绕{name}的小规模可控测试建议。{evidence_note}",
        "objective": "验证已知卖点和目标人群表达，不承诺曝光、转化或收益。",
        "audience_segments": [
            {
                "segment_name": "已知目标用户",
                "description": product.get("target_audience") or "目标人群资料不足",
                "rationale": "仅使用商品档案中的目标人群描述，不生成平台人群包 ID。",
            }
        ],
        "budget_plan": {
            "total_budget": "1000.00",
            "currency": "CNY",
            "allocation": [
                {
                    "channel_or_test": "创意方向 A",
                    "amount": "500.00",
                    "rationale": "作为可调整的测试预算建议，不执行真实扣费。",
                },
                {
                    "channel_or_test": "创意方向 B",
                    "amount": "500.00",
                    "rationale": "保留对照组，最终金额由人工决定。",
                },
            ],
            "rationale": "先用有限预算验证假设；系统不修改任何广告账户预算。",
        },
        "creative_tests": [
            {
                "test_name": "核心卖点表达对比",
                "asset_reference": asset_reference,
                "hypothesis": "不同卖点表达可能产生不同用户反馈，需要实际数据验证。",
                "success_metric": "上线后比较同口径点击和转化数据；当前无 CTR、CVR 或 ROI 结论。",
            }
        ],
        "bid_strategy": {
            "strategy_name": "人工审核后的保守测试",
            "rationale": "当前缺乏真实投放数据，不给出自动出价指令。",
            "constraints": ["不得自动修改出价", "达到人工预算上限后停止测试"],
        },
        "risk_controls": [
            {
                "risk": "现有信息不足以预测收益或转化率。",
                "mitigation": "将建议视为待验证假设，人工确认后再进入独立实验计划。",
            }
        ],
        "next_steps": [
            "人工复核人群、预算和素材引用。",
            "补充真实投放数据后再评估 CTR、CVR 和 ROI。",
        ],
    }


def _ad_experiment_output(context: dict[str, Any]) -> dict[str, Any]:
    product = context["product"]
    recommendation = context["confirmed_recommendation"]
    asset = context.get("approved_asset")
    link = context.get("active_promotion_link")
    budget = recommendation["budget_plan"]["total_budget"]
    bound_data = []
    if asset:
        bound_data.append(f"素材 {asset['asset_reference']}")
    if link:
        bound_data.append(f"链接 {link['link_reference']}")
    binding_note = "、".join(bound_data) if bound_data else "未绑定审核素材或活跃推广链接"
    return {
        "experiment_name": f"{product['name']}·核心卖点验证",
        "target_text": f"验证已确认建议中的目标：{recommendation['objective']}",
        "audience_text": product.get("target_audience") or "目标人群资料不足，执行前需人工补充",
        "budget_amount": budget,
        "success_metric_text": (
            f"{binding_note}；上线后以同口径点击率和落地页访问量作为观察指标，"
            "当前不预设 CTR、CVR 或 ROI 数值。"
        ),
        "hypothesis_text": "待验证假设：目标用户可能对突出已知核心卖点的内容产生更积极反馈。",
    }


def _review_report_output(context: dict[str, Any]) -> dict[str, Any]:
    metrics = context["aggregated_performance"]
    period = context["review_period"]
    clicks = metrics["total_clicks"]
    ctr = metrics["overall_ctr"]
    roi = metrics["overall_roi"]
    roi_evidence = (
        f"overall_roi={roi}"
        if roi is not None
        else "overall_roi=null（总支出为 0）"
    )
    return {
        "summary": (
            f"本周期纳入 {period['included_count']} 条经营记录，"
            f"总曝光 {metrics['total_impressions']}、总点击 {clicks}、"
            f"总转化 {metrics['total_conversions']}。"
        ),
        "insights": [
            {
                "title": "整体流量表现",
                "finding": "点击和转化表现应以系统汇总原始指标为准。",
                "evidence": f"total_clicks={clicks}; overall_ctr={ctr}",
            },
            {
                "title": "投入产出表现",
                "finding": "当前周期投入产出仅代表已录入经营数据。",
                "evidence": (
                    f"total_spend={metrics['total_spend']}; "
                    f"total_revenue={metrics['total_revenue']}; {roi_evidence}"
                ),
            },
        ],
        "problem_judgements": [
            {
                "problem": "现有数据只能支持周期内部判断，缺少外部基准。",
                "evidence": (
                    f"included_count={period['included_count']}; "
                    f"excluded_count={period['excluded_count']}"
                ),
                "severity": "medium",
            }
        ],
        "next_actions": [
            {
                "action": "由运营人员复核分组表现并决定下一轮实验。",
                "rationale": "报告只解释已录入数据，不自动修改数据或启动新流程。",
                "priority": "high",
            }
        ],
    }


def _read_context(user_prompt: str, marker: str) -> dict[str, Any]:
    _, separator, payload = user_prompt.partition(marker)
    if not separator:
        raise ValueError("Prompt is missing structured context")
    return json.loads(payload)
