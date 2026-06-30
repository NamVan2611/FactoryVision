"""Application entry point.

Module 0 (current): a minimal FastAPI app that proves the foundation works --
settings load, logging is wired, runtime directories are created and a
``/health`` endpoint responds. Subsequent modules (database, inspection, MQTT,
TCP, WebSocket, security) will be mounted here via routers and lifespan hooks.

Run (development):

    cd backend
    uvicorn main:app --reload --port 8000

or simply::

    python main.py
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

# Allow `python main.py` execution by ensuring `backend/` is importable as root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app import __version__  # noqa: E402
from app.api import api_router, register_exception_handlers  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.utils import get_logger, setup_logging  # noqa: E402

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks.

    Future modules will start the MQTT client, TCP server and DB engine here.
    """
    logger.info("Starting %s v%s (env=%s)", settings.app_name, __version__, settings.app_env)
    settings.ensure_runtime_dirs()
    logger.info("Runtime directories ready.")
    yield
    logger.info("Shutting down %s.", settings.app_name)


def create_app() -> FastAPI:
    """Application factory (testable, avoids import-time side effects)."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness probe used by the dashboard and orchestration tooling."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": __version__,
            "env": settings.app_env,
        }

    # Domain -> HTTP error translation and feature routers (Module 3).
    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
