"""SQLAlchemy ORM models for the Smart Factory Vision Inspection system.

Eight tables, each with a primary key, appropriate foreign keys, indexes on
frequently-queried columns, and ``created_at`` / ``updated_at`` via
:class:`TimestampMixin`.

Relationship map
----------------
* Machine 1--* InspectionHistory, Alarm, MachineLog, ProductionReport
* Product 1--* InspectionHistory, ProductionReport
* Operator 1--* InspectionHistory, Alarm
* InspectionHistory 1--* InspectionImage
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import (
    AlarmSeverity,
    DefectType,
    ImageKind,
    InspectionResult,
    MachineLogLevel,
    MachineStatus,
)


class Machine(Base, TimestampMixin):
    """A physical machine / station on the production line."""

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    line: Mapped[str] = mapped_column(String(50), index=True, nullable=False, default="LINE-1")
    status: Mapped[MachineStatus] = mapped_column(
        String(20), default=MachineStatus.IDLE, nullable=False
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    uph: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    inspections: Mapped[List["InspectionHistory"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    alarms: Mapped[List["Alarm"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    logs: Mapped[List["MachineLog"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    reports: Mapped[List["ProductionReport"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )


class Product(Base, TimestampMixin):
    """A product model/SKU that can be inspected."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    inspections: Mapped[List["InspectionHistory"]] = relationship(
        back_populates="product"
    )
    reports: Mapped[List["ProductionReport"]] = relationship(back_populates="product")


class Operator(Base, TimestampMixin):
    """A human operator responsible for a station/shift."""

    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    shift: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    inspections: Mapped[List["InspectionHistory"]] = relationship(
        back_populates="operator"
    )
    alarms: Mapped[List["Alarm"]] = relationship(back_populates="operator")


class InspectionHistory(Base, TimestampMixin):
    """One vision-inspection event and its result."""

    __tablename__ = "inspection_history"
    __table_args__ = (
        Index("ix_inspection_machine_time", "machine_id", "inspected_at"),
        Index("ix_inspection_result", "result"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("operators.id", ondelete="SET NULL"), index=True, nullable=True
    )

    result: Mapped[InspectionResult] = mapped_column(String(10), nullable=False)
    defect_type: Mapped[DefectType] = mapped_column(
        String(20), default=DefectType.NONE, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    processing_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounding_box: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, comment="JSON [x, y, w, h] of the defect region."
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    machine: Mapped["Machine"] = relationship(back_populates="inspections")
    product: Mapped[Optional["Product"]] = relationship(back_populates="inspections")
    operator: Mapped[Optional["Operator"]] = relationship(back_populates="inspections")
    images: Mapped[List["InspectionImage"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )


class InspectionImage(Base, TimestampMixin):
    """Image artefact (original or annotated) tied to an inspection."""

    __tablename__ = "inspection_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_history.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[ImageKind] = mapped_column(
        String(20), default=ImageKind.ORIGINAL, nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    inspection: Mapped["InspectionHistory"] = relationship(back_populates="images")


class Alarm(Base, TimestampMixin):
    """A machine/process alarm event."""

    __tablename__ = "alarms"
    __table_args__ = (Index("ix_alarm_machine_time", "machine_id", "raised_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("operators.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[AlarmSeverity] = mapped_column(
        String(20), default=AlarmSeverity.WARNING, nullable=False
    )
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    machine: Mapped["Machine"] = relationship(back_populates="alarms")
    operator: Mapped[Optional["Operator"]] = relationship(back_populates="alarms")


class MachineLog(Base, TimestampMixin):
    """Time-series event log for a machine (state changes, commands, telemetry)."""

    __tablename__ = "machine_logs"
    __table_args__ = (Index("ix_machinelog_machine_time", "machine_id", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[MachineLogLevel] = mapped_column(
        String(10), default=MachineLogLevel.INFO, nullable=False
    )
    event: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    machine: Mapped["Machine"] = relationship(back_populates="logs")


class ProductionReport(Base, TimestampMixin):
    """Aggregated production KPIs for a machine/product over a period."""

    __tablename__ = "production_reports"
    __table_args__ = (
        Index("ix_report_machine_date", "machine_id", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    report_date: Mapped[datetime] = mapped_column(Date, index=True, nullable=False)

    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yield_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    uph: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downtime_minutes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    defect_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_inspection_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    machine: Mapped["Machine"] = relationship(back_populates="reports")
    product: Mapped[Optional["Product"]] = relationship(back_populates="reports")
