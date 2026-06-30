"""ORM models package.

Importing this package registers every table on ``Base.metadata`` (needed by
``init_db``) and re-exports the entities and enums for convenient access:

>>> from app.models import Machine, InspectionResult
"""

from app.models.entities import (
    Alarm,
    InspectionHistory,
    InspectionImage,
    Machine,
    MachineLog,
    Operator,
    Product,
    ProductionReport,
)
from app.models.enums import (
    AlarmSeverity,
    DefectType,
    ImageKind,
    InspectionResult,
    MachineLogLevel,
    MachineStatus,
)

__all__ = [
    # entities
    "Machine",
    "Product",
    "Operator",
    "InspectionHistory",
    "InspectionImage",
    "Alarm",
    "MachineLog",
    "ProductionReport",
    # enums
    "MachineStatus",
    "InspectionResult",
    "DefectType",
    "AlarmSeverity",
    "ImageKind",
    "MachineLogLevel",
]
