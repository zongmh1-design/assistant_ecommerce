"""Whitelist mapping from existing business records into advertising advice input."""

from app.models.creative_plan import CreativePlan
from app.models.generated_asset import GeneratedAsset
from app.models.product import Product
from app.models.product_diagnosis import ProductDiagnosis
from app.models.promotion_link import PromotionLink
from app.schemas.ad_recommendation import (
    AdAssetContext, AdCreativePlanContext, AdDiagnosisContext,
    AdProductContext, AdPromotionLinkContext, AdRecommendationContext,
)


def build_ad_recommendation_context(
    product: Product,
    diagnosis: ProductDiagnosis | None,
    selected_plans: list[CreativePlan],
    approved_assets: list[GeneratedAsset],
    active_links: list[PromotionLink],
) -> AdRecommendationContext:
    return AdRecommendationContext(
        product=AdProductContext(
            name=product.name, platform=product.platform, category=product.category,
            price=product.price, target_audience=product.target_audience,
            selling_points=product.selling_points,
        ),
        latest_diagnosis=(
            AdDiagnosisContext(
                positioning=diagnosis.positioning,
                audience_insights=diagnosis.audience_insights,
                pain_points=diagnosis.pain_points,
                selling_point_analysis=diagnosis.selling_point_analysis,
                risks=diagnosis.risks,
                recommendations=diagnosis.recommendations,
            ) if diagnosis is not None else None
        ),
        selected_creative_plans=[
            AdCreativePlanContext(
                plan_type=plan.plan_type, title=plan.title, content_json=plan.content_json
            ) for plan in selected_plans
        ],
        approved_assets=[
            AdAssetContext(
                asset_reference=(
                    f"asset_{position}_{asset.asset_type.value}_v{asset.version_no}"
                ),
                asset_type=asset.asset_type, version_no=asset.version_no,
                usage_scene=asset.usage_scene, score=asset.score, tags_json=asset.tags_json,
            ) for position, asset in enumerate(approved_assets, start=1)
        ],
        active_promotion_links=[
            AdPromotionLinkContext(
                link_name=link.link_name, scene_text=link.scene_text,
                utm_json=link.utm_json, click_count=link.click_count,
            ) for link in active_links
        ],
    )
