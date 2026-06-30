"""Production history endpoints.

Read-only views over ``inspection_history`` consumed by the dashboard's
"Recent Production" panel and the History page.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from app.api.dependencies import InspectionServiceDep
from app.schemas.entities import InspectionRead

router = APIRouter(prefix="/history", tags=["history"])


@router.get(
    "",
    response_model=List[InspectionRead],
    summary="List recent inspections (newest first)",
)
async def list_history(
    service: InspectionServiceDep,
    machine_id: Optional[int] = Query(None, description="Filter by machine id."),
    limit: int = Query(20, ge=1, le=500, description="Max rows to return."),
) -> List[InspectionRead]:
    """Return the most recent inspections, optionally filtered by machine."""
    rows = service.recent(machine_id=machine_id, limit=limit)
    return [InspectionRead.model_validate(r) for r in rows]


__all__ = ["router"]
