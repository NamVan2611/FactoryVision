"""Machine control & telemetry endpoints.

Exposes lifecycle commands (start/stop/reset) and read endpoints used by the
dashboard. The actual MQTT command dispatch is added in a later module; here we
update authoritative machine state in the database.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.dependencies import MachineServiceDep
from app.schemas.entities import MachineRead, MachineUpdate
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/machine", tags=["machine"])


@router.get("", response_model=List[MachineRead], summary="List active machines")
async def list_machines(service: MachineServiceDep) -> List[MachineRead]:
    """Return all active machines ordered by code."""
    return [MachineRead.model_validate(m) for m in service.list_active()]


@router.get("/{machine_id}", response_model=MachineRead, summary="Get a machine")
async def get_machine(machine_id: int, service: MachineServiceDep) -> MachineRead:
    """Return a single machine by id (404 if missing)."""
    return MachineRead.model_validate(service.get(machine_id))


@router.post("/{machine_id}/start", response_model=MachineRead, summary="Start machine")
async def start_machine(machine_id: int, service: MachineServiceDep) -> MachineRead:
    """Transition a machine to RUNNING."""
    return MachineRead.model_validate(service.start(machine_id))


@router.post("/{machine_id}/stop", response_model=MachineRead, summary="Stop machine")
async def stop_machine(machine_id: int, service: MachineServiceDep) -> MachineRead:
    """Transition a machine to STOPPED."""
    return MachineRead.model_validate(service.stop(machine_id))


@router.post("/{machine_id}/reset", response_model=MachineRead, summary="Reset machine")
async def reset_machine(machine_id: int, service: MachineServiceDep) -> MachineRead:
    """Reset telemetry counters and move the machine to IDLE."""
    return MachineRead.model_validate(service.reset(machine_id))


@router.patch(
    "/{machine_id}/telemetry",
    response_model=MachineRead,
    summary="Update machine telemetry",
)
async def update_telemetry(
    machine_id: int, payload: MachineUpdate, service: MachineServiceDep
) -> MachineRead:
    """Apply a partial telemetry update (status/temperature/speed/uph)."""
    machine = service.update_telemetry(
        machine_id,
        status=payload.status,
        temperature=payload.temperature,
        speed=payload.speed,
        uph=payload.uph,
    )
    return MachineRead.model_validate(machine)


__all__ = ["router"]
