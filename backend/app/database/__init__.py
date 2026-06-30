"""Database infrastructure package.

Exposes the SQLAlchemy engine/session factory and the declarative ``Base`` so
the rest of the app (repositories, models, FastAPI dependencies) can import a
single, configured persistence layer.
"""

from app.database.base import Base
from app.database.session import (
    SessionLocal,
    engine,
    get_db,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "session_scope",
]
