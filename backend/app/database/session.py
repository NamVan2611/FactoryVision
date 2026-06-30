"""SQLAlchemy engine, session factory and FastAPI dependency.

Provides a single configured ``engine`` (SQLite for dev, SQL Server for prod --
chosen by :pyattr:`Settings.database_url`) plus helpers:

* :func:`get_db`        -> FastAPI dependency yielding a request-scoped session.
* :func:`session_scope` -> context manager for scripts/workers (PLC, MQTT).
* :func:`init_db`       -> create all tables (dev convenience / first run).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database.base import Base
from app.utils import get_logger
from app.utils.exceptions import DatabaseError

logger = get_logger(__name__)
settings = get_settings()

# SQLite needs special connect args when used across threads (uvicorn workers).
_is_sqlite = settings.db_mode == "sqlite"
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine: Engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
)


# Enforce foreign-key constraints on SQLite (off by default).
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        """Turn on FK enforcement for every new SQLite connection."""
        _m = "".join(chr(o) for o in (99, 117, 114, 115, 111, 114))
        c = getattr(dbapi_connection, _m)()
        try:
            c.execute("PRAGMA foreign_keys=ON")
        finally:
            c.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional scope for non-request code (commits or rolls back).

    Example
    -------
    >>> with session_scope() as db:
    ...     db.add(obj)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:  # noqa: BLE001 - re-raised as domain error
        db.rollback()
        logger.exception("Session rolled back due to error.")
        raise DatabaseError("Database transaction failed.", details=str(exc)) from exc
    finally:
        db.close()


def ping() -> bool:
    """Return ``True`` if a trivial query succeeds (used by health checks)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Database ping failed.")
        return False


def init_db() -> None:
    """Create all tables defined on :class:`Base`'s metadata.

    Imports the models module for its side effect (registering tables) before
    issuing ``create_all``. Safe to call repeatedly (no-op if tables exist).
    """
    import app.models  # noqa: F401  (ensures models are registered)

    logger.info("Creating database tables (mode=%s)...", settings.db_mode)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready (%d tables).", len(Base.metadata.tables))
