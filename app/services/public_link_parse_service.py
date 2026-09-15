"""Public-link parse task lifecycle and explicit confirmation use cases."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.integrations.public_link_parser import (
    PublicLinkParseResult,
    PublicLinkParser,
    PublicLinkParserError,
)
from app.models.competitor import Competitor, PublicLinkParseTask, PublicLinkParseTaskStatus
from app.repositories.competitor_repository import CompetitorRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.public_link_parse_task_repository import PublicLinkParseTaskRepository
from app.schemas.competitor import PublicLinkParseTaskCreate


class PublicLinkParseService:
    def __init__(self, db: Session, parser: PublicLinkParser) -> None:
        self.db = db
        self.parser = parser
        self.products = ProductRepository(db)
        self.tasks = PublicLinkParseTaskRepository(db)
        self.competitors = CompetitorRepository(db)

    def create_task(
        self, product_id: int, payload: PublicLinkParseTaskCreate
    ) -> PublicLinkParseTask:
        self._require_product(product_id)
        task = PublicLinkParseTask(
            product_id=product_id,
            source_url=str(payload.source_url),
            task_status=PublicLinkParseTaskStatus.PENDING,
            attempts=0,
        )
        self.tasks.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, product_id: int, task_id: int) -> PublicLinkParseTask:
        self._require_product(product_id)
        task = self.tasks.get_by_id_and_product_id(task_id, product_id)
        if task is None:
            raise _task_not_found(task_id)
        return task

    def run_task(self, product_id: int, task_id: int) -> PublicLinkParseTask:
        task = self.get_task(product_id, task_id)
        if task.confirmed_competitor_id is not None:
            raise _task_state_conflict("Confirmed task cannot be run again")
        if task.task_status not in {
            PublicLinkParseTaskStatus.PENDING,
            PublicLinkParseTaskStatus.FAILED,
        }:
            raise _task_state_conflict(
                f"Task in {task.task_status.value} state cannot be run"
            )

        self.tasks.update(
            task,
            {
                "task_status": PublicLinkParseTaskStatus.RUNNING,
                "attempts": task.attempts + 1,
                "result_json": None,
                "error_message": None,
            },
        )
        self.db.commit()
        self.db.refresh(task)

        try:
            result = self.parser.parse(task.source_url)
        except PublicLinkParserError as exc:
            return self._mark_failed(task, str(exc))
        except Exception:
            return self._mark_failed(task, "Public link parser failed unexpectedly")

        self.tasks.update(
            task,
            {
                "task_status": PublicLinkParseTaskStatus.SUCCEEDED,
                "result_json": result.model_dump(mode="json"),
                "error_message": None,
            },
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def confirm(self, product_id: int, task_id: int) -> Competitor:
        self._require_product(product_id)
        task = self.tasks.get_for_confirmation(task_id, product_id)
        if task is None:
            raise _task_not_found(task_id)
        if task.task_status is not PublicLinkParseTaskStatus.SUCCEEDED:
            raise _task_state_conflict("Only succeeded task can be confirmed")
        if task.confirmed_competitor_id is not None:
            raise AppError(
                status_code=409,
                code="link_parse_task_already_confirmed",
                message="Task has already created a competitor",
            )
        if task.result_json is None:
            raise _task_state_conflict("Succeeded task has no parse result")

        result = PublicLinkParseResult.model_validate(task.result_json)
        competitor = Competitor(
            product_id=task.product_id,
            name=result.name,
            platform=result.platform,
            url=task.source_url,
            price=result.price,
            sales_hint=result.sales_hint,
            title=result.title,
            main_image=str(result.main_image) if result.main_image is not None else None,
            selling_points=result.selling_points,
            review_keywords=result.review_keywords,
        )

        try:
            self.competitors.add(competitor)
            self.db.flush()
            self.tasks.update(task, {"confirmed_competitor_id": competitor.id})
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(competitor)
        return competitor

    def _mark_failed(
        self, task: PublicLinkParseTask, error_message: str
    ) -> PublicLinkParseTask:
        self.tasks.update(
            task,
            {
                "task_status": PublicLinkParseTaskStatus.FAILED,
                "result_json": None,
                "error_message": error_message,
            },
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def _require_product(self, product_id: int) -> None:
        if self.products.get_by_id(product_id) is None:
            raise AppError(
                status_code=404,
                code="product_not_found",
                message=f"Product {product_id} was not found",
            )


def _task_not_found(task_id: int) -> AppError:
    return AppError(
        status_code=404,
        code="link_parse_task_not_found",
        message=f"Public link parse task {task_id} was not found",
    )


def _task_state_conflict(message: str) -> AppError:
    return AppError(status_code=409, code="invalid_link_parse_task_state", message=message)
