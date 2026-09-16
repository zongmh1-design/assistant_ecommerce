"""Database access dedicated to GeneratedAsset records."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.generated_asset import (
    AssetReviewStatus,
    GeneratedAsset,
    GeneratedAssetType,
)


class GeneratedAssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, asset: GeneratedAsset) -> GeneratedAsset:
        self.db.add(asset)
        return asset

    def get_by_job_id(self, job_id: int) -> GeneratedAsset | None:
        return self.db.scalar(
            select(GeneratedAsset).where(
                GeneratedAsset.generation_job_id == job_id
            )
        )

    def get_by_id_and_product_id(
        self, asset_id: int, product_id: int
    ) -> GeneratedAsset | None:
        return self.db.scalar(
            select(GeneratedAsset).where(
                GeneratedAsset.id == asset_id,
                GeneratedAsset.product_id == product_id,
            )
        )

    def get_latest_approved_by_product(
        self, product_id: int
    ) -> GeneratedAsset | None:
        return self.db.scalar(
            select(GeneratedAsset)
            .where(
                GeneratedAsset.product_id == product_id,
                GeneratedAsset.review_status == AssetReviewStatus.APPROVED,
            )
            .order_by(GeneratedAsset.created_at.desc(), GeneratedAsset.id.desc())
            .limit(1)
        )

    def list_approved_for_ad_context(self, product_id: int) -> list[GeneratedAsset]:
        return list(
            self.db.scalars(
                select(GeneratedAsset)
                .where(
                    GeneratedAsset.product_id == product_id,
                    GeneratedAsset.review_status == AssetReviewStatus.APPROVED,
                )
                .order_by(GeneratedAsset.created_at.desc(), GeneratedAsset.id.desc())
            )
        )

    def next_version_no(
        self,
        *,
        product_id: int,
        creative_plan_id: int,
        asset_type: GeneratedAssetType,
    ) -> int:
        maximum = self.db.scalar(
            select(func.max(GeneratedAsset.version_no)).where(
                GeneratedAsset.product_id == product_id,
                GeneratedAsset.creative_plan_id == creative_plan_id,
                GeneratedAsset.asset_type == asset_type,
            )
        )
        return (maximum or 0) + 1

    def list_by_product(
        self,
        *,
        product_id: int,
        asset_type: GeneratedAssetType | None,
        review_status: AssetReviewStatus | None,
        creative_plan_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[GeneratedAsset], int]:
        conditions = [GeneratedAsset.product_id == product_id]
        if asset_type is not None:
            conditions.append(GeneratedAsset.asset_type == asset_type)
        if review_status is not None:
            conditions.append(GeneratedAsset.review_status == review_status)
        if creative_plan_id is not None:
            conditions.append(GeneratedAsset.creative_plan_id == creative_plan_id)
        items = list(
            self.db.scalars(
                select(GeneratedAsset)
                .where(*conditions)
                .order_by(GeneratedAsset.created_at.desc(), GeneratedAsset.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count()).select_from(GeneratedAsset).where(*conditions)
        ) or 0
        return items, total
