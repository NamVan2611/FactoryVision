"""Centralised FastAPI exception handlers.

Translate our domain :class:`~app.utils.exceptions.AppError` hierarchy into
consistent JSON responses so clients always receive the same envelope:

    {"error": {"type": "...", "message": "...", "details": ...}}

This keeps routers free of try/except boilerplate (they just raise domain
errors) and guarantees a uniform contract for the Electron dashboard.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.utils import get_logger
from app.utils.exceptions import AppError

logger = get_logger(__name__)


def _envelope(error_type: str, message: str, details: object | None = None) -> dict:
    """Build the standard error response body."""
    return {"error": {"type": error_type, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers to the given application instance."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        # 5xx are unexpected -> log with stack; 4xx are client issues -> info.
        if exc.status_code >= 500:
            logger.exception("AppError (%s): %s", exc.status_code, exc.message)
        else:
            logger.info("AppError (%s): %s", exc.status_code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(type(exc).__name__, exc.message, exc.details),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_envelope("InternalServerError", "An unexpected error occurred."),
        )


__all__ = ["register_exception_handlers"]
