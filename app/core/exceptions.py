"""Application-level exceptions and their global HTTP representation."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        content: dict[str, Any] = {
            "error": {"code": exc.code, "message": exc.message}
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )
