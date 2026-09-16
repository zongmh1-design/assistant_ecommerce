"""Admin-only composition endpoint for the complete backend demonstration."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.demo_data import DemoDataResponse
from app.services.demo_data_service import DemoDataService


router = APIRouter(tags=["workspace-demo"])


@router.post("/workspace/demo-data", response_model=DemoDataResponse)
def initialize_demo_data(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DemoDataResponse:
    return DemoDataService(db).initialize(current_user.id)
