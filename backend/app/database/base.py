"""Declarative base and common column mixins.

* :class:`Base` is the single SQLAlchemy 2.0 declarative base for all models.
* :class:`TimestampMixin` adds ``created_at`` / ``updated_at`` columns that are
  populated automatically at the database level, satisfying the project
  requirement that *every* table tracks creation and update times.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base."""


class TimestampMixin:
    """Adds self-managing ``created_at`` and ``updated_at`` timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Row creation time (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update time (UTC).",
    )
