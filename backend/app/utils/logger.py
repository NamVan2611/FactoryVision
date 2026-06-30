"""Centralised logging configuration.

Provides a single :func:`setup_logging` entry point that configures the root
logger with:

* A coloured, human-readable **console** handler.
* A rotating **file** handler (``logs/app.log``) capturing everything.
* A dedicated rotating **error file** handler (``logs/error.log``) for
  ``WARNING`` and above, so problems are easy to triage.

Other modules simply call :func:`get_logger(__name__)` and never touch handler
configuration themselves -- this keeps logging consistent across the API,
inspection engine, MQTT/TCP workers and background tasks.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.config import get_settings

# Guard so handlers are attached only once even if setup runs multiple times
# (e.g. uvicorn reload, pytest re-imports).
_CONFIGURED: bool = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ANSI colours for the console (gracefully ignored on non-TTY redirects).
_COLOURS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[41m",  # red background
}
_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    """Console formatter that colourises the level name."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        colour = _COLOURS.get(record.levelname, "")
        record.levelname = f"{colour}{record.levelname}{_RESET}" if colour else record.levelname
        return super().format(record)


def setup_logging() -> None:
    """Configure the root logger. Idempotent: safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    log_dir: Path = settings.log_dir_path
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()  # avoid duplicate logs under uvicorn reload

    # --- Console handler ---
    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(level)
    console.setFormatter(_ColourFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console)

    plain = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # --- Rotating file handler (everything) ---
    app_file = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    app_file.setLevel(level)
    app_file.setFormatter(plain)
    root.addHandler(app_file)

    # --- Rotating error file handler (WARNING+) ---
    error_file = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    error_file.setLevel(logging.WARNING)
    error_file.setFormatter(plain)
    root.addHandler(error_file)

    # Tame noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _CONFIGURED = True
    logging.getLogger(__name__).info(
        "Logging initialised (level=%s, dir=%s)", settings.log_level, log_dir
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module logger, ensuring logging is configured first.

    Parameters
    ----------
    name:
        Usually ``__name__`` of the calling module. ``None`` returns the root.
    """
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
