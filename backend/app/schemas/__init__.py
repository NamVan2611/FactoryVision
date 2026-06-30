"""Pydantic schemas package -- re-exports for ergonomic imports.

>>> from app.schemas import MachineRead, InspectionCreate, Page
"""

from app.schemas.common import Message, ORMModel, Page, PageMeta, TimestampSchema
from app.schemas.entities import (
    AlarmCreate,
    AlarmRead,
    InspectionCreate,
    InspectionImageRead,
    InspectionRead,
    MachineCreate,
    MachineLogCreate,
    MachineLogRead,
    MachineRead,
    MachineUpdate,
    OperatorCreate,
    OperatorRead,
    OperatorUpdate,
    ProductCreate,
    ProductionReportRead,
    ProductRead,
    ProductUpdate,
    ReportSummary,
)
from app.schemas.vision import (
    BoundingBox,
    Defect,
    InspectionResultDTO,
)

__all__ = [
    # common
    "ORMModel",
    "TimestampSchema",
    "Page",
    "PageMeta",
    "Message",
    # machine
    "MachineCreate",
    "MachineUpdate",
    "MachineRead",
    # product
    "ProductCreate",
    "ProductUpdate",
    "ProductRead",
    # operator
    "OperatorCreate",
    "OperatorUpdate",
    "OperatorRead",
    # inspection
    "InspectionCreate",
    "InspectionRead",
    "InspectionImageRead",
    # alarm
    "AlarmCreate",
    "AlarmRead",
    # machine log
    "MachineLogCreate",
    "MachineLogRead",
    # report
    "ProductionReportRead",
    "ReportSummary",
    # vision
    "BoundingBox",
    "Defect",
    "InspectionResultDTO",
]
