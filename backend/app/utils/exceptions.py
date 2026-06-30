"""Domain-specific exception hierarchy.

Centralising exceptions lets the API layer translate them into consistent HTTP
responses (see the FastAPI exception handlers in Module 3) while the business
and infrastructure layers stay free of HTTP concerns (SOLID: dependency rule).
"""

from __future__ import annotations

from typing import Any, Optional


class AppError(Exception):
    """Base class for all application errors.

    Parameters
    ----------
    message:
        Human-readable message safe to surface to clients.
    status_code:
        Suggested HTTP status code used by the API layer.
    details:
        Optional structured context for logging / debugging.
    """

    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    """A requested entity does not exist."""

    status_code = 404


class ValidationError(AppError):
    """Input failed business-rule validation."""

    status_code = 422


class ConflictError(AppError):
    """The operation conflicts with the current state (e.g. duplicate)."""

    status_code = 409


class AuthenticationError(AppError):
    """Caller could not be authenticated (bad/missing credentials)."""

    status_code = 401


class AuthorizationError(AppError):
    """Caller is authenticated but not permitted to perform the action."""

    status_code = 403


class InspectionError(AppError):
    """The vision inspection pipeline failed (bad image, decode error, ...)."""

    status_code = 422


class CameraError(InspectionError):
    """A camera source could not acquire or open a frame/device."""

    status_code = 503


class DatabaseError(AppError):
    """A persistence operation failed unexpectedly."""

    status_code = 500


class CommunicationError(AppError):
    """An MQTT / TCP / external integration failed."""

    status_code = 502
