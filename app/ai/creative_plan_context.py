"""Build the minimal Product + latest Diagnosis context for creative planning."""

from app.models.product import Product
from app.models.product_diagnosis import ProductDiagnosis
from app.schemas.creative_plan import (
    CreativeDiagnosisContext,
    CreativePlanContext,
    CreativeProductContext,
)


def build_creative_plan_context(
    product: Product,
    diagnosis: ProductDiagnosis | None,
) -> CreativePlanContext:
    diagnosis_context = None
    if diagnosis is not None:
        diagnosis_context = CreativeDiagnosisContext(
            positioning=diagnosis.positioning,
            price_band=diagnosis.price_band,
            audience_insights=diagnosis.audience_insights,
            pain_points=diagnosis.pain_points,
            selling_point_analysis=diagnosis.selling_point_analysis,
            risks=diagnosis.risks,
            recommendations=diagnosis.recommendations,
        )
    return CreativePlanContext(
        product=CreativeProductContext(
            name=product.name,
            platform=product.platform,
            category=product.category,
            price=product.price,
            target_audience=product.target_audience,
            selling_points=product.selling_points,
        ),
        diagnosis=diagnosis_context,
    )
