"""Application services: orchestrate repositories + domain logic.

The service layer is the *Application* tier in our Clean Architecture. It is the
only place where business rules live; routers stay thin (HTTP <-> DTO) and
repositories stay dumb (CRUD/queries). Services accept a SQLAlchemy ``Session``
and compose one or more repositories.

Persistence note
----------------
:class:`~app.repositories.base.BaseRepository` exposes ``add()`` to stage a new
row (auto-flush populates its primary key). Updates need no explicit call: the
Unit-of-Work pattern of the SQLAlchemy ``Session`` tracks attribute changes on
managed instances and writes them on ``commit()``.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.entities import Alarm, InspectionHistory, Machine, MachineLog
from app.models.enums import (
    DefectType,
    MachineLogLevel,
    MachineStatus,
)
from app.repositories import (
    AlarmRepository,
    InspectionRepository,
    MachineLogRepository,
    MachineRepository,
    OperatorRepository,
    ProductRepository,
)
from app.schemas.vision import InspectionResultDTO
from app.utils import get_logger
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.time_utils import utc_now

logger = get_logger(__name__)


class MachineService:
    """Machine lifecycle, telemetry and command handling."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.machines = MachineRepository(db)
        self.logs = MachineLogRepository(db)

    def get(self, machine_id: int) -> Machine:
        """Return a machine or raise :class:`NotFoundError`."""
        machine = self.machines.get(machine_id)
        if machine is None:
            raise NotFoundError(f"Machine id={machine_id} not found.")
        return machine

    def get_by_code(self, code: str) -> Machine:
        """Return a machine by its unique business code or raise 404."""
        machine = self.machines.get_by_code(code)
        if machine is None:
            raise NotFoundError(f"Machine code={code!r} not found.")
        return machine

    def list_active(self) -> Sequence[Machine]:
        """Return all active machines (ordered by code)."""
        return self.machines.list_active()

    def _log(self, machine_id: int, event: str, message: str = "") -> None:
        """Stage a machine log entry in the current transaction."""
        self.logs.add(
            MachineLog(
                machine_id=machine_id,
                level=MachineLogLevel.INFO,
                event=event,
                message=message,
                logged_at=utc_now(),
            )
        )

    def _set_status(
        self, machine_id: int, status: MachineStatus, event: str
    ) -> Machine:
        """Apply a status transition, log it and commit atomically."""
        machine = self.get(machine_id)
        machine.status = status  # tracked by the session; written on commit
        self._log(machine_id, event, f"status -> {status}")
        self.db.commit()
        self.db.refresh(machine)
        logger.info("Machine %s %s.", machine.code, event)
        return machine

    def start(self, machine_id: int) -> Machine:
        """Transition the machine to RUNNING."""
        return self._set_status(machine_id, MachineStatus.RUNNING, "START")

    def stop(self, machine_id: int) -> Machine:
        """Transition the machine to STOPPED."""
        return self._set_status(machine_id, MachineStatus.STOPPED, "STOP")

    def reset(self, machine_id: int) -> Machine:
        """Reset telemetry counters and move the machine to IDLE."""
        machine = self.get(machine_id)
        machine.status = MachineStatus.IDLE
        machine.temperature = 0.0
        machine.speed = 0.0
        machine.uph = 0
        self._log(machine_id, "RESET", "telemetry cleared")
        self.db.commit()
        self.db.refresh(machine)
        logger.info("Machine %s RESET.", machine.code)
        return machine

    def update_telemetry(
        self,
        machine_id: int,
        *,
        status: Optional[MachineStatus] = None,
        temperature: Optional[float] = None,
        speed: Optional[float] = None,
        uph: Optional[int] = None,
    ) -> Machine:
        """Apply telemetry coming from the PLC/TCP feed (partial update)."""
        machine = self.get(machine_id)
        if status is not None:
            machine.status = status
        if temperature is not None:
            machine.temperature = temperature
        if speed is not None:
            machine.speed = speed
        if uph is not None:
            machine.uph = uph
        self.db.commit()
        self.db.refresh(machine)
        return machine


class AlarmService:
    """Raise and acknowledge machine alarms."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.alarms = AlarmRepository(db)

    def raise_alarm(
        self,
        machine_id: int,
        code: str,
        message: str,
        *,
        operator_id: Optional[int] = None,
    ) -> Alarm:
        """Create and persist a new (unacknowledged) alarm."""
        alarm = self.alarms.add(
            Alarm(
                machine_id=machine_id,
                operator_id=operator_id,
                code=code,
                message=message,
                raised_at=utc_now(),
            )
        )
        self.db.commit()
        self.db.refresh(alarm)
        logger.warning("ALARM raised machine=%s code=%s", machine_id, code)
        return alarm

    def acknowledge(self, alarm_id: int) -> Alarm:
        """Mark an alarm as acknowledged."""
        alarm = self.alarms.get(alarm_id)
        if alarm is None:
            raise NotFoundError(f"Alarm id={alarm_id} not found.")
        alarm.is_acknowledged = True
        alarm.acknowledged_at = utc_now()
        self.db.commit()
        self.db.refresh(alarm)
        return alarm

    def list_open(
        self, *, machine_id: Optional[int] = None, limit: int = 50
    ) -> Sequence[Alarm]:
        """Return unacknowledged alarms, newest first."""
        return self.alarms.list_open(machine_id=machine_id, limit=limit)


class InspectionService:
    """Persist vision results and answer history queries."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.inspections = InspectionRepository(db)
        self.machines = MachineRepository(db)
        self.products = ProductRepository(db)
        self.operators = OperatorRepository(db)

    def record(
        self,
        dto: InspectionResultDTO,
        *,
        machine_id: int,
        product_id: Optional[int] = None,
        operator_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> InspectionHistory:
        """Persist an :class:`InspectionResultDTO` into ``inspection_history``.

        Foreign keys are validated up-front so the API returns a clean 404/422
        instead of a low-level integrity error.
        """
        if self.machines.get(machine_id) is None:
            raise NotFoundError(f"Machine id={machine_id} not found.")
        if product_id is not None and self.products.get(product_id) is None:
            raise NotFoundError(f"Product id={product_id} not found.")
        if operator_id is not None and self.operators.get(operator_id) is None:
            raise NotFoundError(f"Operator id={operator_id} not found.")

        bbox = None
        primary = (
            max(dto.defects, key=lambda d: d.confidence) if dto.defects else None
        )
        if primary is not None and primary.bounding_box is not None:
            b = primary.bounding_box
            bbox = json.dumps([b.x, b.y, b.width, b.height])

        record = self.inspections.add(
            InspectionHistory(
                machine_id=machine_id,
                product_id=product_id,
                operator_id=operator_id,
                result=dto.result,
                defect_type=primary.type if primary else DefectType.NONE,
                confidence=dto.confidence,
                processing_ms=dto.processing_ms,
                bounding_box=bbox,
                notes=notes,
                inspected_at=utc_now(),
            )
        )
        self.db.commit()
        self.db.refresh(record)
        logger.info(
            "Inspection recorded id=%s machine=%s result=%s",
            record.id, machine_id, dto.result,
        )
        return record

    def recent(
        self, *, machine_id: Optional[int] = None, limit: int = 20
    ) -> Sequence[InspectionHistory]:
        """Return the most recent inspections, newest first."""
        return self.inspections.recent(machine_id=machine_id, limit=limit)

    def get(self, inspection_id: int) -> InspectionHistory:
        """Return a single inspection or raise 404."""
        rec = self.inspections.get(inspection_id)
        if rec is None:
            raise NotFoundError(f"Inspection id={inspection_id} not found.")
        return rec


class ReportService:
    """Compute production KPIs over a time window."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.inspections = InspectionRepository(db)

    def summary(
        self,
        start: datetime,
        end: datetime,
        *,
        machine_id: Optional[int] = None,
    ) -> dict:
        """Return aggregate KPIs (PASS/FAIL/yield/defect-rate/avg time)."""
        if end < start:
            raise ValidationError("`end` must be on or after `start`.")

        pass_count, fail_count = self.inspections.pass_fail_counts(
            start, end, machine_id=machine_id
        )
        total = pass_count + fail_count
        rows = self.inspections.in_range(start, end, machine_id=machine_id)
        avg_ms = sum(r.processing_ms for r in rows) / len(rows) if rows else 0.0
        yield_rate = (pass_count / total * 100.0) if total else 0.0
        defect_rate = (fail_count / total * 100.0) if total else 0.0
        return {
            "start": start,
            "end": end,
            "machine_id": machine_id,
            "total_count": total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "yield_rate": round(yield_rate, 2),
            "defect_rate": round(defect_rate, 2),
            "avg_inspection_ms": round(avg_ms, 2),
        }


__all__ = [
    "MachineService",
    "AlarmService",
    "InspectionService",
    "ReportService",
]
