"""Top-level REST API router."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.products import router as products_router
from app.api.routes.skus import router as skus_router
from app.api.routes.stores import router as stores_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(skus_router)
api_router.include_router(inventory_router)
api_router.include_router(competitors_router)
