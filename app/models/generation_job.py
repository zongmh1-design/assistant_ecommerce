"""Media generation job state and its append-only event timeline."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.creative_plan import CreativePlan
    from app.models.generated_asset import GeneratedAsset
    from app.models.product import Product


class GenerationJobKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class GenerationJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class GenerationJobEventType(str, Enum):
    CREATED = "created"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_REQUESTED = "retry_requested"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_generation_jobs_attempts_nonnegative"),
        CheckConstraint("max_attempts >= 1", name="ck_generation_jobs_max_attempts_positive"),
        CheckConstraint(
            "attempts <= max_attempts",
            name="ck_generation_jobs_attempts_within_max",
        ),
        Index(
            "ix_generation_jobs_product_kind_status",
            "product_id",
            "job_kind",
            "job_status",
        ),
        Index(
            "ix_generation_jobs_status_locked_at",
            "job_status",
            "locked_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    creative_plan_id: Mapped[int] = mapped_column(
        ForeignKey("creative_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    job_kind: Mapped[GenerationJobKind] = mapped_column(
        SqlEnum(
            GenerationJobKind,
            name="generation_job_kind",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    job_status: Mapped[GenerationJobStatus] = mapped_column(
        SqlEnum(
            GenerationJobStatus,
            name="generation_job_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=GenerationJobStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="generation_jobs")
    creative_plan: Mapped["CreativePlan"] = relationship(back_populates="generation_jobs")
    events: Mapped[list["GenerationJobEvent"]] = relationship(
        back_populates="job",
        passive_deletes=True,
        order_by="GenerationJobEvent.id",
    )
    generated_asset: Mapped["GeneratedAsset | None"] = relationship(
        back_populates="generation_job",
        passive_deletes=True,
        uselist=False,
    )


class GenerationJobEvent(Base):
    __tablename__ = "generation_job_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[GenerationJobEventType] = mapped_column(
        SqlEnum(
            GenerationJobEventType,
            name="generation_job_event_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    event_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[GenerationJob] = relationship(back_populates="events")
