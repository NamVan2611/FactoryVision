"""FastAPI dependency providers.

These wire the request-scoped database :class:`~sqlalchemy.orm.Session` (from
:func:`app.database.session.get_db`) into our service classes. Routers depend on
*services*, never on repositories or the session directly -- this keeps the HTTP
layer thin and the wiring centralised (SOLID: dependency inversion).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import (
    AlarmService,
    InspectionService,
    MachineService,
    ReportService,
)

# A reusable type alias for the DB session dependency.
DbSession = Annotated[Session, Depends(get_db)]


def get_machine_service(db: DbSession) -> MachineService:
    """Provide a request-scoped :class:`MachineService`."""
    return MachineService(db)


def get_alarm_service(db: DbSession) -> AlarmService:
    """Provide a request-scoped :class:`AlarmService`."""
    return AlarmService(db)


def get_inspection_service(db: DbSession) -> InspectionService:
    """Provide a request-scoped :class:`InspectionService`."""
    return InspectionService(db)


def get_report_service(db: DbSession) -> ReportService:
    """Provide a request-scoped :class:`ReportService`."""
    return ReportService(db)


# Convenient annotated aliases used by route signatures.
MachineServiceDep = Annotated[MachineService, Depends(get_machine_service)]
AlarmServiceDep = Annotated[AlarmService, Depends(get_alarm_service)]
InspectionServiceDep = Annotated[InspectionService, Depends(get_inspection_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


__all__ = [
    "DbSession",
    "MachineServiceDep",
    "AlarmServiceDep",
    "InspectionServiceDep",
    "ReportServiceDep",
    "get_machine_service",
    "get_alarm_service",
    "get_inspection_service",
    "get_report_service",
]
