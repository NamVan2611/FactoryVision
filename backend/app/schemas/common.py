"""Shared Pydantic base classes and generic response wrappers."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base schema for read models mapped from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(ORMModel):
    """Mixin exposing the audit timestamps present on every table."""

    created_at: datetime
    updated_at: datetime


class PageMeta(BaseModel):
    """Pagination metadata returned alongside list endpoints."""

    total: int = Field(..., ge=0, description="Total matching rows.")
    page: int = Field(1, ge=1, description="Current 1-based page number.")
    size: int = Field(20, ge=1, le=200, description="Page size.")


class Page(BaseModel, Generic[T]):
    """Generic paginated response container."""

    items: List[T]
    meta: PageMeta


class Message(BaseModel):
    """Simple message envelope for acknowledgement-style responses."""

    detail: str
    success: bool = True
    data: Optional[dict] = None
