"""Whitelist mapping for one experiment based on an explicit recommendation."""

from app.models.ad_recommendation import AdRecommendation
from app.models.generated_asset import GeneratedAsset
from app.models.product import Product
from app.models.promotion_link import PromotionLink
from app.schemas.ad_experiment import (
    AdExperimentContext, ExperimentAssetContext, ExperimentLinkContext,
    ExperimentProductContext, ExperimentRecommendationContext,
)


def build_ad_experiment_context(
    product: Product,
    recommendation: AdRecommendation,
    asset: GeneratedAsset | None,
    link: PromotionLink | None,
) -> AdExperimentContext:
    return AdExperimentContext(
        product=ExperimentProductContext(
            name=product.name, platform=product.platform, category=product.category,
            price=product.price, target_audience=product.target_audience,
            selling_points=product.selling_points,
        ),
        confirmed_recommendation=ExperimentRecommendationContext(
            summary=recommendation.summary_text,
            objective=recommendation.objective_text,
            audience_segments=recommendation.audience_segments_json,
            budget_plan=recommendation.budget_plan_json,
            creative_tests=recommendation.creative_tests_json,
            bid_strategy=recommendation.bid_strategy_json,
            risk_controls=recommendation.risk_controls_json,
            next_steps=recommendation.next_steps_json,
        ),
        approved_asset=(
            ExperimentAssetContext(
                asset_reference=f"asset_{asset.asset_type.value}_v{asset.version_no}",
                asset_type=asset.asset_type, version_no=asset.version_no,
                usage_scene=asset.usage_scene, score=asset.score, tags_json=asset.tags_json,
            ) if asset is not None else None
        ),
        active_promotion_link=(
            ExperimentLinkContext(
                link_reference="promotion_link_1", link_name=link.link_name,
                scene_text=link.scene_text, utm_json=link.utm_json,
                click_count=link.click_count,
            ) if link is not None else None
        ),
    )
