"""Pydantic request/response schemas for the domain entities.

Each entity exposes (where it makes sense):
* ``*Create`` -- payload for POST,
* ``*Update`` -- partial payload for PATCH (all optional),
* ``*Read``   -- response model mapped from the ORM object.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    AlarmSeverity,
    DefectType,
    ImageKind,
    InspectionResult,
    MachineLogLevel,
    MachineStatus,
)
from app.schemas.common import ORMModel, TimestampSchema


# --------------------------------------------------------------------------- #
# Machine
# --------------------------------------------------------------------------- #
class MachineCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=120)
    line: str = Field("LINE-1", max_length=50)


class MachineUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    line: Optional[str] = Field(None, max_length=50)
    status: Optional[MachineStatus] = None
    temperature: Optional[float] = None
    speed: Optional[float] = None
    uph: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class MachineRead(TimestampSchema):
    id: int
    code: str
    name: str
    line: str
    status: MachineStatus
    temperature: float
    speed: float
    uph: int
    is_active: bool


# --------------------------------------------------------------------------- #
# Product
# --------------------------------------------------------------------------- #
class ProductCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=120)
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductRead(TimestampSchema):
    id: int
    code: str
    name: str
    description: Optional[str]
    is_active: bool


# --------------------------------------------------------------------------- #
# Operator
# --------------------------------------------------------------------------- #
class OperatorCreate(BaseModel):
    employee_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=120)
    shift: Optional[str] = Field(None, max_length=20)


class OperatorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    shift: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class OperatorRead(TimestampSchema):
    id: int
    employee_id: str
    name: str
    shift: Optional[str]
    is_active: bool


# --------------------------------------------------------------------------- #
# Inspection image
# --------------------------------------------------------------------------- #
class InspectionImageRead(ORMModel):
    id: int
    inspection_id: int
    kind: ImageKind
    file_path: str
    width: Optional[int]
    height: Optional[int]


# --------------------------------------------------------------------------- #
# Inspection history
# --------------------------------------------------------------------------- #
class InspectionCreate(BaseModel):
    machine_id: int
    product_id: Optional[int] = None
    operator_id: Optional[int] = None
    result: InspectionResult
    defect_type: DefectType = DefectType.NONE
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    processing_ms: float = Field(0.0, ge=0.0)
    bounding_box: Optional[str] = None
    notes: Optional[str] = None
    inspected_at: Optional[datetime] = None


class InspectionRead(TimestampSchema):
    id: int
    machine_id: int
    product_id: Optional[int]
    operator_id: Optional[int]
    result: InspectionResult
    defect_type: DefectType
    confidence: float
    processing_ms: float
    bounding_box: Optional[str]
    notes: Optional[str]
    inspected_at: datetime
    images: list[InspectionImageRead] = []


# --------------------------------------------------------------------------- #
# Alarm
# --------------------------------------------------------------------------- #
class AlarmCreate(BaseModel):
    machine_id: int
    operator_id: Optional[int] = None
    code: str = Field(..., max_length=50)
    message: str = Field(..., max_length=255)
    severity: AlarmSeverity = AlarmSeverity.WARNING
    raised_at: Optional[datetime] = None


class AlarmRead(TimestampSchema):
    id: int
    machine_id: int
    operator_id: Optional[int]
    code: str
    message: str
    severity: AlarmSeverity
    is_acknowledged: bool
    raised_at: datetime
    acknowledged_at: Optional[datetime]


# --------------------------------------------------------------------------- #
# Machine log
# --------------------------------------------------------------------------- #
class MachineLogCreate(BaseModel):
    machine_id: int
    level: MachineLogLevel = MachineLogLevel.INFO
    event: str = Field(..., max_length=80)
    message: Optional[str] = None
    logged_at: Optional[datetime] = None


class MachineLogRead(TimestampSchema):
    id: int
    machine_id: int
    level: MachineLogLevel
    event: str
    message: Optional[str]
    logged_at: datetime


# --------------------------------------------------------------------------- #
# Production report
# --------------------------------------------------------------------------- #
class ProductionReportRead(TimestampSchema):
    id: int
    machine_id: int
    product_id: Optional[int]
    report_date: date
    total_count: int
    pass_count: int
    fail_count: int
    yield_rate: float
    uph: int
    downtime_minutes: float
    defect_rate: float
    avg_inspection_ms: float


# --------------------------------------------------------------------------- #
# Report summary (computed on the fly by ReportService)
# --------------------------------------------------------------------------- #
class ReportSummary(BaseModel):
    """Aggregate KPIs over an arbitrary ``[start, end]`` window."""

    start: datetime
    end: datetime
    machine_id: Optional[int] = None
    total_count: int
    pass_count: int
    fail_count: int
    yield_rate: float
    defect_rate: float
    avg_inspection_ms: float
