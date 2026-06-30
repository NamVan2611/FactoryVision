"""Concrete repositories with entity-specific queries.

Each class binds :class:`BaseRepository` to a model and adds the query helpers
the services need (lookups by business key, recent-N, time-range filters, KPI
aggregation, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
from app.models.enums import InspectionResult
from app.repositories.base import BaseRepository


class MachineRepository(BaseRepository[Machine]):
    """Persistence for :class:`Machine`."""

    def __init__(self, db: Session) -> None:
        super().__init__(Machine, db)

    def get_by_code(self, code: str) -> Optional[Machine]:
        """Return the machine identified by its unique business ``code``."""
        return self.get_by(code=code)

    def list_active(self) -> Sequence[Machine]:
        """Return all active machines ordered by code."""
        stmt = select(Machine).where(Machine.is_active.is_(True)).order_by(Machine.code)
        return self.db.execute(stmt).scalars().all()


class ProductRepository(BaseRepository[Product]):
    """Persistence for :class:`Product`."""

    def __init__(self, db: Session) -> None:
        super().__init__(Product, db)

    def get_by_code(self, code: str) -> Optional[Product]:
        return self.get_by(code=code)


class OperatorRepository(BaseRepository[Operator]):
    """Persistence for :class:`Operator`."""

    def __init__(self, db: Session) -> None:
        super().__init__(Operator, db)

    def get_by_employee_id(self, employee_id: str) -> Optional[Operator]:
        return self.get_by(employee_id=employee_id)


class InspectionRepository(BaseRepository[InspectionHistory]):
    """Persistence for :class:`InspectionHistory` plus KPI aggregation."""

    def __init__(self, db: Session) -> None:
        super().__init__(InspectionHistory, db)

    def recent(self, *, machine_id: Optional[int] = None, limit: int = 20):
        """Return the most recent inspections, optionally filtered by machine."""
        stmt = select(InspectionHistory).order_by(InspectionHistory.inspected_at.desc())
        if machine_id is not None:
            stmt = stmt.where(InspectionHistory.machine_id == machine_id)
        return self.db.execute(stmt.limit(limit)).scalars().all()

    def in_range(self, start: datetime, end: datetime, *, machine_id: Optional[int] = None):
        """Return inspections whose ``inspected_at`` falls within ``[start, end]``."""
        stmt = select(InspectionHistory).where(
            InspectionHistory.inspected_at >= start,
            InspectionHistory.inspected_at <= end,
        )
        if machine_id is not None:
            stmt = stmt.where(InspectionHistory.machine_id == machine_id)
        return self.db.execute(stmt).scalars().all()

    def pass_fail_counts(
        self, start: datetime, end: datetime, *, machine_id: Optional[int] = None
    ) -> tuple[int, int]:
        """Return ``(pass_count, fail_count)`` for the given window."""
        stmt = (
            select(InspectionHistory.result, func.count())
            .where(
                InspectionHistory.inspected_at >= start,
                InspectionHistory.inspected_at <= end,
            )
            .group_by(InspectionHistory.result)
        )
        if machine_id is not None:
            stmt = stmt.where(InspectionHistory.machine_id == machine_id)
        counts = {row[0]: row[1] for row in self.db.execute(stmt).all()}
        return (
            int(counts.get(InspectionResult.PASS, 0)),
            int(counts.get(InspectionResult.FAIL, 0)),
        )


class InspectionImageRepository(BaseRepository[InspectionImage]):
    """Persistence for :class:`InspectionImage`."""

    def __init__(self, db: Session) -> None:
        super().__init__(InspectionImage, db)

    def for_inspection(self, inspection_id: int) -> Sequence[InspectionImage]:
        stmt = select(InspectionImage).where(
            InspectionImage.inspection_id == inspection_id
        )
        return self.db.execute(stmt).scalars().all()


class AlarmRepository(BaseRepository[Alarm]):
    """Persistence for :class:`Alarm`."""

    def __init__(self, db: Session) -> None:
        super().__init__(Alarm, db)

    def list_open(self, *, machine_id: Optional[int] = None, limit: int = 50):
        """Return unacknowledged alarms, newest first."""
        stmt = (
            select(Alarm)
            .where(Alarm.is_acknowledged.is_(False))
            .order_by(Alarm.raised_at.desc())
        )
        if machine_id is not None:
            stmt = stmt.where(Alarm.machine_id == machine_id)
        return self.db.execute(stmt.limit(limit)).scalars().all()


class MachineLogRepository(BaseRepository[MachineLog]):
    """Persistence for :class:`MachineLog`."""

    def __init__(self, db: Session) -> None:
        super().__init__(MachineLog, db)

    def recent(self, machine_id: int, *, limit: int = 100):
        stmt = (
            select(MachineLog)
            .where(MachineLog.machine_id == machine_id)
            .order_by(MachineLog.logged_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()


class ProductionReportRepository(BaseRepository[ProductionReport]):
    """Persistence for :class:`ProductionReport`."""

    def __init__(self, db: Session) -> None:
        super().__init__(ProductionReport, db)

    def for_machine_date(
        self, machine_id: int, report_date
    ) -> Optional[ProductionReport]:
        return self.get_by(machine_id=machine_id, report_date=report_date)
