"""Append and paginate PromotionLinkClick records."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.promotion_link import PromotionLinkClick


class PromotionLinkClickRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, click: PromotionLinkClick) -> PromotionLinkClick:
        self.db.add(click)
        return click

    def list_by_link(
        self, *, link_id: int, offset: int, limit: int
    ) -> tuple[list[PromotionLinkClick], int]:
        items = list(
            self.db.scalars(
                select(PromotionLinkClick)
                .where(PromotionLinkClick.promotion_link_id == link_id)
                .order_by(
                    PromotionLinkClick.clicked_at.desc(),
                    PromotionLinkClick.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count())
            .select_from(PromotionLinkClick)
            .where(PromotionLinkClick.promotion_link_id == link_id)
        ) or 0
        return items, total
