"""Database access dedicated to PromotionLink records and atomic counters."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.promotion_link import PromotionLink, PromotionLinkStatus


class PromotionLinkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, link: PromotionLink) -> PromotionLink:
        self.db.add(link)
        return link

    def tracking_code_exists(self, tracking_code: str) -> bool:
        return self.db.scalar(
            select(PromotionLink.id).where(
                PromotionLink.tracking_code == tracking_code
            )
        ) is not None

    def get_by_tracking_code(self, tracking_code: str) -> PromotionLink | None:
        return self.db.scalar(
            select(PromotionLink).where(
                PromotionLink.tracking_code == tracking_code
            )
        )

    def get_by_id_and_product_id(
        self, link_id: int, product_id: int
    ) -> PromotionLink | None:
        return self.db.scalar(
            select(PromotionLink).where(
                PromotionLink.id == link_id,
                PromotionLink.product_id == product_id,
            )
        )

    def list_by_product(
        self,
        *,
        product_id: int,
        status: PromotionLinkStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[PromotionLink], int]:
        conditions = [PromotionLink.product_id == product_id]
        if status is not None:
            conditions.append(PromotionLink.status == status)
        items = list(
            self.db.scalars(
                select(PromotionLink)
                .where(*conditions)
                .order_by(PromotionLink.created_at.desc(), PromotionLink.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(PromotionLink).where(*conditions)
        ) or 0
        return items, total

    def increment_click_count_atomic(self, link_id: int) -> bool:
        result = self.db.execute(
            update(PromotionLink)
            .where(
                PromotionLink.id == link_id,
                PromotionLink.status == PromotionLinkStatus.ACTIVE,
            )
            .values(click_count=PromotionLink.click_count + 1)
        )
        return result.rowcount == 1

    def list_active_for_ad_context(self, product_id: int) -> list[PromotionLink]:
        return list(
            self.db.scalars(
                select(PromotionLink)
                .where(
                    PromotionLink.product_id == product_id,
                    PromotionLink.status == PromotionLinkStatus.ACTIVE,
                )
                .order_by(PromotionLink.created_at.desc(), PromotionLink.id.desc())
            )
        )
