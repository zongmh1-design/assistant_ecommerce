"""Top-level REST API router."""

from fastapi import APIRouter

from app.api.routes.ad_recommendations import router as ad_recommendations_router
from app.api.routes.ad_experiments import router as ad_experiments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.creative_plans import router as creative_plans_router
from app.api.routes.demo_data import router as demo_data_router
from app.api.routes.generation_jobs import router as generation_jobs_router
from app.api.routes.generated_assets import router as generated_assets_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.products import router as products_router
from app.api.routes.product_diagnoses import router as product_diagnoses_router
from app.api.routes.promotion_links import router as promotion_links_router
from app.api.routes.performance_records import router as performance_records_router
from app.api.routes.review_reports import router as review_reports_router
from app.api.routes.skus import router as skus_router
from app.api.routes.stores import router as stores_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(skus_router)
api_router.include_router(inventory_router)
api_router.include_router(competitors_router)
api_router.include_router(product_diagnoses_router)
api_router.include_router(creative_plans_router)
api_router.include_router(demo_data_router)
api_router.include_router(generation_jobs_router)
api_router.include_router(generated_assets_router)
api_router.include_router(promotion_links_router)
api_router.include_router(ad_recommendations_router)
api_router.include_router(ad_experiments_router)
api_router.include_router(performance_records_router)
api_router.include_router(review_reports_router)
