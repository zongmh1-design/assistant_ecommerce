"""Map ORM business records to the minimal product-diagnosis input contract."""

from app.models.competitor import Competitor
from app.models.product import Product
from app.schemas.product_diagnosis import (
    DiagnosisCompetitorContext,
    DiagnosisProductContext,
    ProductDiagnosisContext,
)


def build_product_diagnosis_context(
    product: Product, competitors: list[Competitor]
) -> ProductDiagnosisContext:
    return ProductDiagnosisContext(
        product=DiagnosisProductContext(
            name=product.name,
            platform=product.platform,
            category=product.category,
            price=product.price,
            cost=product.cost,
            target_audience=product.target_audience,
            selling_points=product.selling_points,
        ),
        competitors=[
            DiagnosisCompetitorContext(
                name=item.name,
                platform=item.platform,
                price=item.price,
                title=item.title,
                sales_hint=item.sales_hint,
                selling_points=item.selling_points,
                review_keywords=item.review_keywords,
            )
            for item in competitors
        ],
    )
