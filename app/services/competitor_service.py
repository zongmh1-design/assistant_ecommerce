"""Competitor manual-entry use cases."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.competitor import Competitor
from app.repositories.competitor_repository import CompetitorRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.competitor import CompetitorCreate, CompetitorUpdate


class CompetitorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.competitors = CompetitorRepository(db)

    def create(self, product_id: int, payload: CompetitorCreate) -> Competitor:
        self._require_product(product_id)
        competitor = Competitor(product_id=product_id, **_competitor_data(payload))
        self.competitors.add(competitor)
        self.db.commit()
        self.db.refresh(competitor)
        return competitor

    def list(
        self, *, product_id: int, page: int, page_size: int
    ) -> tuple[list[Competitor], int]:
        self._require_product(product_id)
        return self.competitors.list_by_product(
            product_id=product_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get(self, competitor_id: int) -> Competitor:
        competitor = self.competitors.get_by_id(competitor_id)
        if competitor is None:
            raise _competitor_not_found(competitor_id)
        return competitor

    def update(self, competitor_id: int, payload: CompetitorUpdate) -> Competitor:
        competitor = self.get(competitor_id)
        changes = _competitor_data(payload, exclude_unset=True)
        self.competitors.update(competitor, changes)
        self.db.commit()
        self.db.refresh(competitor)
        return competitor

    def _require_product(self, product_id: int) -> None:
        if self.products.get_by_id(product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )


def _competitor_data(
    payload: CompetitorCreate | CompetitorUpdate, *, exclude_unset: bool = False
) -> dict[str, object]:
    data = payload.model_dump(exclude_unset=exclude_unset)
    for field_name in ("url", "main_image"):
        if field_name in data and data[field_name] is not None:
            data[field_name] = str(data[field_name])
    return data


def _competitor_not_found(competitor_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="competitor_not_found",
        message=f"Competitor {competitor_id} was not found",
    )
