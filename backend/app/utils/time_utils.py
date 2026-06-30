"""Time helpers.

A tiny wrapper around :mod:`datetime` so the whole codebase uses **timezone-aware
UTC** timestamps consistently (avoids the classic naive-vs-aware bugs and makes
SQL Server / SQLite timestamps comparable across machines).
"""

from __future__ import annotations

from datetime import datetime, timezone

# ISO-8601 with milliseconds, e.g. "2026-06-30T02:44:05.123Z"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC :class:`datetime`."""
    return datetime.now(timezone.utc)


# Backward-compatible alias. Some modules import ``utc_now`` (snake style);
# keep both names pointing at the same implementation to avoid churn.
utc_now = utcnow


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with trailing ``Z``."""
    return utcnow().strftime(ISO_FORMAT)


def to_iso(dt: datetime) -> str:
    """Serialise a :class:`datetime` to ISO-8601 (coerces to UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)


__all__ = ["ISO_FORMAT", "utcnow", "utc_now", "utcnow_iso", "to_iso"]
