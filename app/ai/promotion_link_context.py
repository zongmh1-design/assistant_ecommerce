"""Whitelist mapping for promotion-link suggestion inputs."""

from app.models.creative_plan import CreativePlan
from app.models.generated_asset import GeneratedAsset
from app.models.product import Product
from app.schemas.promotion_link import (
    PromotionAssetContext,
    PromotionCreativePlanContext,
    PromotionLinkSuggestionContext,
    PromotionProductContext,
)


def build_promotion_link_context(
    product: Product,
    selected_plan: CreativePlan | None,
    approved_asset: GeneratedAsset | None,
) -> PromotionLinkSuggestionContext:
    return PromotionLinkSuggestionContext(
        product=PromotionProductContext(
            name=product.name,
            platform=product.platform,
            category=product.category,
            target_audience=product.target_audience,
            selling_points=product.selling_points,
        ),
        selected_creative_plan=(
            PromotionCreativePlanContext(
                plan_type=selected_plan.plan_type,
                title=selected_plan.title,
                content_json=selected_plan.content_json,
            )
            if selected_plan is not None
            else None
        ),
        approved_asset=(
            PromotionAssetContext(
                asset_type=approved_asset.asset_type,
                usage_scene=approved_asset.usage_scene,
                tags_json=approved_asset.tags_json,
            )
            if approved_asset is not None
            else None
        ),
    )
