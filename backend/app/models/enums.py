"""Domain enumerations shared across models, schemas and services.

Centralising these as :class:`enum.Enum` subclasses keeps magic strings out of
the codebase, gives editors/linters autocompletion, and lets SQLAlchemy persist
them as constrained ``VARCHAR`` columns (portable across SQLite & SQL Server).
"""

from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    """String-valued enum that serialises to its plain value (JSON-friendly)."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class MachineStatus(StrEnum):
    """Lifecycle/operational state of a production machine."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"


class InspectionResult(StrEnum):
    """Outcome of a single vision inspection."""

    PASS = "PASS"
    FAIL = "FAIL"


class DefectType(StrEnum):
    """Categories of defect the vision system can report."""

    NONE = "NONE"
    COLOR = "COLOR"          # sai màu
    DIMENSION = "DIMENSION"  # sai kích thước
    MISSING_PART = "MISSING_PART"  # thiếu linh kiện
    SCRATCH = "SCRATCH"      # xước bề mặt
    UNKNOWN = "UNKNOWN"


class AlarmSeverity(StrEnum):
    """Severity levels for machine/process alarms."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ImageKind(StrEnum):
    """Distinguishes the raw captured frame from the annotated result image."""

    ORIGINAL = "ORIGINAL"
    PROCESSED = "PROCESSED"


class MachineLogLevel(StrEnum):
    """Level for entries in the machine event log."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


__all__ = [
    "StrEnum",
    "MachineStatus",
    "InspectionResult",
    "DefectType",
    "AlarmSeverity",
    "ImageKind",
    "MachineLogLevel",
]
