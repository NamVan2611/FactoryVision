"""REST API package: router aggregation and handler registration.

Exposes a single :data:`api_router` that mounts every feature router under a
common ``/api`` prefix, plus :func:`register_exception_handlers` re-exported for
``main.py`` to wire domain errors to HTTP responses.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.handlers import register_exception_handlers
from app.api.history_router import router as history_router
from app.api.inspection_router import router as inspection_router
from app.api.machine_router import router as machine_router
from app.api.report_router import router as report_router

api_router = APIRouter(prefix="/api")
api_router.include_router(inspection_router)
api_router.include_router(machine_router)
api_router.include_router(history_router)
api_router.include_router(report_router)


__all__ = ["api_router", "register_exception_handlers"]
